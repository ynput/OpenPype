"""Load a layout in Blender."""

import json
from logging import log, warning
import math

import logging
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

from avalon import api, blender
import bpy
import pype.hosts.blender.plugin as plugin


class BlendLayoutLoader(plugin.AssetLoader):
    """Load layout from a .blend file."""

    families = ["layout"]
    representations = ["blend"]

    label = "Link Layout"
    icon = "code-fork"
    color = "orange"

    def _remove(self, objects, obj_container):
        for obj in list(objects):
            if obj.type == 'ARMATURE':
                bpy.data.armatures.remove(obj.data)
            elif obj.type == 'MESH':
                bpy.data.meshes.remove(obj.data)
            elif obj.type == 'CAMERA':
                bpy.data.cameras.remove(obj.data)
            elif obj.type == 'CURVE':
                bpy.data.curves.remove(obj.data)

        for element_container in obj_container.children:
            for child in element_container.children:
                bpy.data.collections.remove(child)
            bpy.data.collections.remove(element_container)

        bpy.data.collections.remove(obj_container)

    def _process(self, libpath, lib_container, container_name, actions):
        relative = bpy.context.preferences.filepaths.use_relative_paths
        with bpy.data.libraries.load(
            libpath, link=True, relative=relative
        ) as (_, data_to):
            data_to.collections = [lib_container]

        scene = bpy.context.scene

        scene.collection.children.link(bpy.data.collections[lib_container])

        layout_container = scene.collection.children[lib_container].make_local()
        layout_container.name = container_name

        objects_local_types = ['MESH', 'CAMERA', 'CURVE']

        objects = []
        armatures = []

        containers = list(layout_container.children)

        for container in layout_container.children:
            if container.name == blender.pipeline.AVALON_CONTAINERS:
                containers.remove(container)

        for container in containers:
            container.make_local()
            objects.extend([
                obj for obj in container.objects
                if obj.type in objects_local_types
            ])
            armatures.extend([
                obj for obj in container.objects
                if obj.type == 'ARMATURE'
            ])
            containers.extend(list(container.children))

        # Link meshes first, then armatures.
        # The armature is unparented for all the non-local meshes,
        # when it is made local.
        for obj in objects + armatures:
            local_obj = obj.make_local()
            if obj.data:
                obj.data.make_local()

            if not local_obj.get(blender.pipeline.AVALON_PROPERTY):
                local_obj[blender.pipeline.AVALON_PROPERTY] = dict()

            avalon_info = local_obj[blender.pipeline.AVALON_PROPERTY]
            avalon_info.update({"container_name": container_name})

            action = actions.get(local_obj.name, None)

            if local_obj.type == 'ARMATURE' and action is not None:
                local_obj.animation_data.action = action

        layout_container.pop(blender.pipeline.AVALON_PROPERTY)

        bpy.ops.object.select_all(action='DESELECT')

        return layout_container

    def process_asset(
        self, context: dict, name: str, namespace: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Optional[List]:
        """
        Arguments:
            name: Use pre-defined name
            namespace: Use pre-defined namespace
            context: Full parenthood of representation to load
            options: Additional settings dictionary
        """

        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]
        lib_container = plugin.asset_name(
            asset, subset
        )
        unique_number = plugin.get_unique_number(
            asset, subset
        )
        namespace = namespace or f"{asset}_{unique_number}"
        container_name = plugin.asset_name(
            asset, subset, unique_number
        )

        container = bpy.data.collections.new(lib_container)
        container.name = container_name
        blender.pipeline.containerise_existing(
            container,
            name,
            namespace,
            context,
            self.__class__.__name__,
        )

        container_metadata = container.get(
            blender.pipeline.AVALON_PROPERTY)

        container_metadata["libpath"] = libpath
        container_metadata["lib_container"] = lib_container

        obj_container = self._process(
            libpath, lib_container, container_name, {})

        container_metadata["obj_container"] = obj_container

        # Save the list of objects in the metadata container
        container_metadata["objects"] = obj_container.all_objects

        # nodes = list(container.objects)
        # nodes.append(container)
        nodes = [container]
        self[:] = nodes
        return nodes

    def update(self, container: Dict, representation: Dict):
        """Update the loaded asset.

        This will remove all objects of the current collection, load the new
        ones and add them to the collection.
        If the objects of the collection are used in another collection they
        will not be removed, only unlinked. Normally this should not be the
        case though.

        Warning:
            No nested collections are supported at the moment!
        """
        collection = bpy.data.collections.get(
            container["objectName"]
        )

        libpath = Path(api.get_representation_path(representation))
        extension = libpath.suffix.lower()

        self.log.info(
            "Container: %s\nRepresentation: %s",
            pformat(container, indent=2),
            pformat(representation, indent=2),
        )

        assert collection, (
            f"The asset is not loaded: {container['objectName']}"
        )
        assert not (collection.children), (
            "Nested collections are not supported."
        )
        assert libpath, (
            "No existing library file found for {container['objectName']}"
        )
        assert libpath.is_file(), (
            f"The file doesn't exist: {libpath}"
        )
        assert extension in plugin.VALID_EXTENSIONS, (
            f"Unsupported file: {libpath}"
        )

        collection_metadata = collection.get(
            blender.pipeline.AVALON_PROPERTY)
        collection_libpath = collection_metadata["libpath"]
        objects = collection_metadata["objects"]
        lib_container = collection_metadata["lib_container"]
        obj_container = collection_metadata["obj_container"]

        normalized_collection_libpath = (
            str(Path(bpy.path.abspath(collection_libpath)).resolve())
        )
        normalized_libpath = (
            str(Path(bpy.path.abspath(str(libpath))).resolve())
        )
        self.log.debug(
            "normalized_collection_libpath:\n  %s\nnormalized_libpath:\n  %s",
            normalized_collection_libpath,
            normalized_libpath,
        )
        if normalized_collection_libpath == normalized_libpath:
            self.log.info("Library already loaded, not updating...")
            return

        actions = {}

        for obj in objects:
            if obj.type == 'ARMATURE':
                if obj.animation_data and obj.animation_data.action:
                    actions[obj.name] = obj.animation_data.action

        self._remove(objects, obj_container)

        obj_container = self._process(
            str(libpath), lib_container, collection.name, actions)

        # Save the list of objects in the metadata container
        collection_metadata["obj_container"] = obj_container
        collection_metadata["objects"] = obj_container.all_objects
        collection_metadata["libpath"] = str(libpath)
        collection_metadata["representation"] = str(representation["_id"])

        bpy.ops.object.select_all(action='DESELECT')

    def remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container (avalon-core:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the container was deleted.

        Warning:
            No nested collections are supported at the moment!
        """

        collection = bpy.data.collections.get(
            container["objectName"]
        )
        if not collection:
            return False
        assert not (collection.children), (
            "Nested collections are not supported."
        )

        collection_metadata = collection.get(
            blender.pipeline.AVALON_PROPERTY)
        objects = collection_metadata["objects"]
        obj_container = collection_metadata["obj_container"]

        self._remove(objects, obj_container)

        bpy.data.collections.remove(collection)

        return True


class UnrealLayoutLoader(plugin.AssetLoader):
    """Load layout published from Unreal."""

    families = ["layout"]
    representations = ["json"]

    label = "Link Layout"
    icon = "code-fork"
    color = "orange"

    def _remove_objects(self, objects):
        for obj in list(objects):
            if obj.type == 'ARMATURE':
                bpy.data.armatures.remove(obj.data)
            elif obj.type == 'MESH':
                bpy.data.meshes.remove(obj.data)
            elif obj.type == 'CAMERA':
                bpy.data.cameras.remove(obj.data)
            elif obj.type == 'CURVE':
                bpy.data.curves.remove(obj.data)
            else:
                self.log.error(
                    f"Object {obj.name} of type {obj.type} not recognized.")

    def _remove_collections(self, collection):
        if collection.children:
            for child in collection.children:
                self._remove_collections(child)
                bpy.data.collections.remove(child)

    def _get_loader(self, loaders, family):
        name = ""
        if family == 'rig':
            name = "BlendRigLoader"
        elif family == 'model':
            name = "BlendModelLoader"

        if name == "":
            return None

        for loader in loaders:
            if loader.__name__ == name:
                return loader
        
        return None

    def set_transform(self, obj, transform):
        location = transform.get('translation')
        rotation = transform.get('rotation')
        scale = transform.get('scale')

        # Y position is inverted in sign because Unreal and Blender have the
        # Y axis mirrored
        obj.location = (
            location.get('x') / 10,
            -location.get('y') / 10,
            location.get('z') / 10
        )
        obj.rotation_euler = (
            rotation.get('x'),
            -rotation.get('y'),
            -rotation.get('z')
        )
        obj.scale = (
            scale.get('x') / 10,
            scale.get('y') / 10,
            scale.get('z') / 10
        )

    def _process(self, libpath,  layout_container, container_name, actions):
        with open(libpath, "r") as fp:
            data = json.load(fp)

        scene = bpy.context.scene
        layout_collection = bpy.data.collections.new(container_name)
        scene.collection.children.link(layout_collection)

        all_loaders = api.discover(api.Loader)

        avalon_container = bpy.data.collections.get(
            blender.pipeline.AVALON_CONTAINERS)

        for element in data:
            reference = element.get('reference')
            family = element.get('family')

            loaders = api.loaders_from_representation(all_loaders, reference)
            loader = self._get_loader(loaders, family)
                
            if not loader:
                continue

            instance_name = element.get('instance_name')

            element_container = api.load(
                loader,
                reference, 
                namespace=instance_name
            )

            if not element_container:
                continue

            avalon_container.children.unlink(element_container)
            layout_container.children.link(element_container)

            element_metadata = element_container.get(
                blender.pipeline.AVALON_PROPERTY)

            # Unlink the object's collection from the scene collection and 
            # link it in the layout collection
            element_collection = element_metadata.get('obj_container')
            scene.collection.children.unlink(element_collection)
            layout_collection.children.link(element_collection)

            objects = element_metadata.get('objects')
            element_metadata['instance_name'] = instance_name

            objects_to_transform = []

            if family == 'rig':
                for o in objects:
                    if o.type == 'ARMATURE':
                        objects_to_transform.append(o)
                        break
            elif family == 'model':
                objects_to_transform = objects

            for o in objects_to_transform:
                self.set_transform(o, element.get('transform'))

                if actions:
                    if o.type == 'ARMATURE':
                        action = actions.get(instance_name, None)

                        if action:
                            if o.animation_data is None:
                                o.animation_data_create()
                            o.animation_data.action = action

        return layout_collection

    def process_asset(self,
                      context: dict,
                      name: str,
                      namespace: Optional[str] = None,
                      options: Optional[Dict] = None):
        """
        Arguments:
            name: Use pre-defined name
            namespace: Use pre-defined namespace
            context: Full parenthood of representation to load
            options: Additional settings dictionary
        """
        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]
        lib_container = plugin.asset_name(
            asset, subset
        )
        unique_number = plugin.get_unique_number(
            asset, subset
        )
        namespace = namespace or f"{asset}_{unique_number}"
        container_name = plugin.asset_name(
            asset, subset, unique_number
        )

        layout_container = bpy.data.collections.new(container_name)
        blender.pipeline.containerise_existing(
            layout_container,
            name,
            namespace,
            context,
            self.__class__.__name__,
        )

        container_metadata = layout_container.get(
            blender.pipeline.AVALON_PROPERTY)

        container_metadata["libpath"] = libpath
        container_metadata["lib_container"] = lib_container
        
        layout_collection = self._process(
            libpath, layout_container, container_name, None)

        container_metadata["obj_container"] = layout_collection

        # Save the list of objects in the metadata container
        container_metadata["objects"] = layout_collection.all_objects

        nodes = [layout_container]
        self[:] = nodes
        return nodes

    def update(self, container: Dict, representation: Dict):
        """Update the loaded asset.

        This will remove all objects of the current collection, load the new
        ones and add them to the collection.
        If the objects of the collection are used in another collection they
        will not be removed, only unlinked. Normally this should not be the
        case though.
        """
        print(container)
        print(container["objectName"])
        layout_container = bpy.data.collections.get(
            container["objectName"]
        )
        libpath = Path(api.get_representation_path(representation))
        extension = libpath.suffix.lower()

        self.log.info(
            "Container: %s\nRepresentation: %s",
            pformat(container, indent=2),
            pformat(representation, indent=2),
        )

        assert layout_container, (
            f"The asset is not loaded: {container['objectName']}"
        )
        assert libpath, (
            "No existing library file found for {container['objectName']}"
        )
        assert libpath.is_file(), (
            f"The file doesn't exist: {libpath}"
        )
        assert extension in plugin.VALID_EXTENSIONS, (
            f"Unsupported file: {libpath}"
        )

        layout_container_metadata = layout_container.get(
            blender.pipeline.AVALON_PROPERTY)
        collection_libpath = layout_container_metadata["libpath"]
        lib_container = layout_container_metadata["lib_container"]
        obj_container = plugin.get_local_collection_with_name(
            layout_container_metadata["obj_container"].name
        )
        objects = obj_container.all_objects

        container_name = obj_container.name

        normalized_collection_libpath = (
            str(Path(bpy.path.abspath(collection_libpath)).resolve())
        )
        normalized_libpath = (
            str(Path(bpy.path.abspath(str(libpath))).resolve())
        )
        self.log.debug(
            "normalized_collection_libpath:\n  %s\nnormalized_libpath:\n  %s",
            normalized_collection_libpath,
            normalized_libpath,
        )
        if normalized_collection_libpath == normalized_libpath:
            self.log.info("Library already loaded, not updating...")
            return

        actions = {}

        for obj in objects:
            if obj.type == 'ARMATURE':
                if obj.animation_data and obj.animation_data.action:
                    obj_cont_name = obj.get(
                        blender.pipeline.AVALON_PROPERTY).get('container_name')
                    obj_cont = plugin.get_local_collection_with_name(
                        obj_cont_name)
                    element_metadata = obj_cont.get(
                        blender.pipeline.AVALON_PROPERTY)
                    instance_name = element_metadata.get('instance_name')
                    actions[instance_name] = obj.animation_data.action

        self._remove_objects(objects)
        self._remove_collections(obj_container)
        bpy.data.collections.remove(obj_container)
        self._remove_collections(layout_container)
        # bpy.data.collections.remove(layout_container)

        layout_collection = self._process(
            libpath, layout_container, container_name, actions)

        layout_container_metadata["obj_container"] = layout_collection
        layout_container_metadata["objects"] = layout_collection.all_objects
        layout_container_metadata["libpath"] = str(libpath)
        layout_container_metadata["representation"] = str(representation["_id"])


    def remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container (avalon-core:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the container was deleted.
        """
        layout_container = bpy.data.collections.get(
            container["objectName"]
        )
        if not layout_container:
            return False
        # assert not (collection.children), (
        #     "Nested collections are not supported."
        # )

        layout_container_metadata = layout_container.get(
            blender.pipeline.AVALON_PROPERTY)
        obj_container = plugin.get_local_collection_with_name(
            layout_container_metadata["obj_container"].name
        )
        objects = obj_container.all_objects

        self._remove_objects(objects)
        self._remove_collections(obj_container)
        bpy.data.collections.remove(obj_container)
        self._remove_collections(layout_container)
        bpy.data.collections.remove(layout_container)

        return True
