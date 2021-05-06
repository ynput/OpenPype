"""Load a layout in Blender."""

from pathlib import Path
from pprint import pformat
from typing import Dict, Optional

import bpy
from pxr import Usd

from avalon import api, blender
import openpype.hosts.blender.api.plugin as plugin
from openpype.lib import get_creator_by_name


class UsdLayoutLoader(plugin.AssetLoader):
    """Load layout published from Usd."""

    families = ["layout"]
    representations = ["usd"]

    label = "Load Usd Layout"
    icon = "code-fork"
    color = "orange"

    animation_creator_name = "CreateAnimation"
    setdress_creator_name = "CreateSetDress"

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

    def _remove(self, layout_container):
        layout_container_metadata = layout_container.get(
            blender.pipeline.AVALON_PROPERTY)

        if layout_container.children:
            for child in layout_container.children:
                child_container = child.get(blender.pipeline.AVALON_PROPERTY)
                child_container['objectName'] = child.name
                api.remove(child_container)

        for c in bpy.data.collections:
            metadata = c.get('avalon')
            if metadata and metadata.get('id') == 'pyblish.avalon.instance':
                if metadata.get('dependencies') == layout_container_metadata.get('representation'):
                    for child in c.children:
                        bpy.data.collections.remove(child)
                    bpy.data.collections.remove(c)
                    break

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

    def _process(
        self, libpath, layout_container, container_name, representation,
        actions, parent
    ):
        stage = Usd.Stage.Open(libpath)

        scene = bpy.context.scene
        layout_collection = bpy.data.collections.new(container_name)
        scene.collection.children.link(layout_collection)

        all_loaders = api.discover(api.Loader)

        avalon_container = bpy.data.collections.get(
            blender.pipeline.AVALON_CONTAINERS)

        for prim_ref in stage.Traverse():
            if prim_ref.GetAttribute('reference'):
                reference = prim_ref.GetAttribute('reference').Get()
                family = prim_ref.GetAttribute('family').Get()

                loaders = api.loaders_from_representation(
                    all_loaders, reference)
                loader = self._get_loader(loaders, family)

                if not loader:
                    continue

                instance_name = prim_ref.GetAttribute('instance_name').Get()

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

                creator_plugin = get_creator_by_name(
                    self.animation_creator_name)
                if not creator_plugin:
                    raise ValueError(
                        "Creator plugin \"{}\" was not found.".format(
                            self.animation_creator_name
                        ))

                if family == 'rig':
                    for o in objects:
                        if o.type == 'ARMATURE':
                            objects_to_transform.append(o)
                            # Create an animation subset for each rig
                            o.select_set(True)
                            asset = api.Session["AVALON_ASSET"]
                            c = api.create(
                                creator_plugin,
                                name="animation_" + element_collection.name,
                                asset=asset,
                                options={"useSelection": True},
                                data={"dependencies": representation})
                            scene.collection.children.unlink(c)
                            parent.children.link(c)
                            o.select_set(False)
                            break
                elif family == 'model':
                    objects_to_transform = objects

                for o in objects_to_transform:
                    location = prim_ref.GetAttribute('xformOp:translate').Get()
                    rotation = prim_ref.GetAttribute('xformOp:rotateXYZ').Get()
                    scale = prim_ref.GetAttribute('xformOp:scale').Get()

                    o.location = (location[0], location[1], location[2])
                    o.rotation_euler = (rotation[0], rotation[1], rotation[2])
                    o.scale = (scale[0], scale[1], scale[2])

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

        # Create a setdress subset to contain all the animation for all
        # the rigs in the layout
        creator_plugin = get_creator_by_name(self.setdress_creator_name)
        if not creator_plugin:
            raise ValueError("Creator plugin \"{}\" was not found.".format(
                self.setdress_creator_name
            ))
        parent = api.create(
            creator_plugin,
            name="animation",
            asset=api.Session["AVALON_ASSET"],
            options={"useSelection": True},
            data={"dependencies": str(context["representation"]["_id"])})

        layout_collection = self._process(
            libpath, layout_container, container_name,
            str(context["representation"]["_id"]), None, parent)

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
        layout_container = bpy.data.collections.get(
            container["objectName"]
        )
        if not layout_container:
            return False

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

        self._remove(layout_container)

        bpy.data.collections.remove(obj_container)

        creator_plugin = get_creator_by_name(self.setdress_creator_name)
        if not creator_plugin:
            raise ValueError("Creator plugin \"{}\" was not found.".format(
                self.setdress_creator_name
            ))

        parent = api.create(
            creator_plugin,
            name="animation",
            asset=api.Session["AVALON_ASSET"],
            options={"useSelection": True},
            data={"dependencies": str(representation["_id"])})

        layout_collection = self._process(
            str(libpath), layout_container, container_name,
            str(representation["_id"]), actions, parent)

        layout_container_metadata["obj_container"] = layout_collection
        layout_container_metadata["objects"] = layout_collection.all_objects
        layout_container_metadata["libpath"] = str(libpath)
        layout_container_metadata["representation"] = str(
            representation["_id"])

    def remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container (openpype:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the container was deleted.
        """
        layout_container = bpy.data.collections.get(
            container["objectName"]
        )
        if not layout_container:
            return False

        layout_container_metadata = layout_container.get(
            blender.pipeline.AVALON_PROPERTY)
        obj_container = plugin.get_local_collection_with_name(
            layout_container_metadata["obj_container"].name
        )

        self._remove(layout_container)

        bpy.data.collections.remove(obj_container)
        bpy.data.collections.remove(layout_container)

        return True
