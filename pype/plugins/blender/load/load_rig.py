"""Load a rig asset in Blender."""

import logging
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

from avalon import api, blender
import bpy
import pype.hosts.blender.plugin as plugin


class BlendRigLoader(plugin.AssetLoader):
    """Load rigs from a .blend file.

    Because they come from a .blend file we can simply link the collection that
    contains the model. There is no further need to 'containerise' it.
    """

    families = ["rig"]
    representations = ["blend"]

    label = "Link Rig"
    icon = "code-fork"
    color = "orange"

    def _remove(self, objects, obj_container):
        for obj in list(objects):
            if obj.type == 'ARMATURE':
                bpy.data.armatures.remove(obj.data)
            elif obj.type == 'MESH':
                bpy.data.meshes.remove(obj.data)

        for child in obj_container.children:
            bpy.data.collections.remove(child)

        bpy.data.collections.remove(obj_container)

    def _process(
        self, libpath, lib_container, container_name,
        action, parent_collection
    ):
        relative = bpy.context.preferences.filepaths.use_relative_paths
        with bpy.data.libraries.load(
            libpath, link=True, relative=relative
        ) as (_, data_to):
            data_to.collections = [lib_container]

        parent = parent_collection

        if parent is None:
            parent = bpy.context.scene.collection

        parent.children.link(bpy.data.collections[lib_container])

        rig_container = parent.children[lib_container].make_local()
        rig_container.name = container_name

        meshes = []
        armatures = [
            obj for obj in rig_container.objects
            if obj.type == 'ARMATURE'
        ]

        for child in rig_container.children:
            local_child = plugin.prepare_data(child, container_name)
            meshes.extend(local_child.objects)

        # Link meshes first, then armatures.
        # The armature is unparented for all the non-local meshes,
        # when it is made local.
        for obj in meshes + armatures:
            local_obj = plugin.prepare_data(obj, container_name)
            plugin.prepare_data(local_obj.data, container_name)

            if not local_obj.get(blender.pipeline.AVALON_PROPERTY):
                local_obj[blender.pipeline.AVALON_PROPERTY] = dict()

            avalon_info = local_obj[blender.pipeline.AVALON_PROPERTY]
            avalon_info.update({"container_name": container_name})

            if local_obj.type == 'ARMATURE' and action is not None:
                local_obj.animation_data.action = action

        rig_container.pop(blender.pipeline.AVALON_PROPERTY)

        bpy.ops.object.select_all(action='DESELECT')

        return rig_container

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
            libpath, lib_container, container_name, None, None)

        container_metadata["obj_container"] = obj_container

        # Save the list of objects in the metadata container
        container_metadata["objects"] = obj_container.all_objects

        nodes = list(container.objects)
        nodes.append(container)
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
        lib_container = collection_metadata["lib_container"]

        obj_container = plugin.get_local_collection_with_name(
            collection_metadata["obj_container"].name
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

        # Get the armature of the rig
        armatures = [obj for obj in objects if obj.type == 'ARMATURE']
        assert(len(armatures) == 1)

        action = None
        if armatures[0].animation_data and armatures[0].animation_data.action:
            action = armatures[0].animation_data.action

        parent = plugin.get_parent_collection(obj_container)

        self._remove(objects, obj_container)

        obj_container = self._process(
            str(libpath), lib_container, container_name, action, parent)

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

        obj_container = plugin.get_local_collection_with_name(
            collection_metadata["obj_container"].name
        )
        objects = obj_container.all_objects

        self._remove(objects, obj_container)

        bpy.data.collections.remove(collection)

        return True
