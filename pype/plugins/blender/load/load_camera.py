"""Load a camera asset in Blender."""

import logging
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

from avalon import api, blender
import bpy
import pype.hosts.blender.plugin

logger = logging.getLogger("pype").getChild("blender").getChild("load_camera")


class BlendCameraLoader(pype.hosts.blender.plugin.AssetLoader):
    """Load a camera from a .blend file.

    Warning:
        Loading the same asset more then once is not properly supported at the
        moment.
    """

    families = ["camera"]
    representations = ["blend"]

    label = "Link Camera"
    icon = "code-fork"
    color = "orange"

    def _remove(self, objects, lib_container):
        for obj in list(objects):
            bpy.data.cameras.remove(obj.data)

        bpy.data.collections.remove(bpy.data.collections[lib_container])

    def _process(self, libpath, lib_container, container_name, actions):

        relative = bpy.context.preferences.filepaths.use_relative_paths
        with bpy.data.libraries.load(
            libpath, link=True, relative=relative
        ) as (_, data_to):
            data_to.collections = [lib_container]

        scene = bpy.context.scene

        scene.collection.children.link(bpy.data.collections[lib_container])

        camera_container = scene.collection.children[lib_container].make_local()

        objects_list = []

        for obj in camera_container.objects:
            local_obj = obj.make_local()
            local_obj.data.make_local()

            if not local_obj.get(blender.pipeline.AVALON_PROPERTY):
                local_obj[blender.pipeline.AVALON_PROPERTY] = dict()

            avalon_info = local_obj[blender.pipeline.AVALON_PROPERTY]
            avalon_info.update({"container_name": container_name})

            if actions[0] is not None:
                if local_obj.animation_data is None:
                    local_obj.animation_data_create()
                local_obj.animation_data.action = actions[0]

            if actions[1] is not None:
                if local_obj.data.animation_data is None:
                    local_obj.data.animation_data_create()
                local_obj.data.animation_data.action = actions[1]

            objects_list.append(local_obj)

        camera_container.pop(blender.pipeline.AVALON_PROPERTY)

        bpy.ops.object.select_all(action='DESELECT')

        return objects_list

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
        lib_container = pype.hosts.blender.plugin.asset_name(asset, subset)
        container_name = pype.hosts.blender.plugin.asset_name(
            asset, subset, namespace
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

        objects_list = self._process(
            libpath, lib_container, container_name, (None, None))

        # Save the list of objects in the metadata container
        container_metadata["objects"] = objects_list

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

        logger.info(
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
        assert extension in pype.hosts.blender.plugin.VALID_EXTENSIONS, (
            f"Unsupported file: {libpath}"
        )

        collection_metadata = collection.get(
            blender.pipeline.AVALON_PROPERTY)
        collection_libpath = collection_metadata["libpath"]
        objects = collection_metadata["objects"]
        lib_container = collection_metadata["lib_container"]

        normalized_collection_libpath = (
            str(Path(bpy.path.abspath(collection_libpath)).resolve())
        )
        normalized_libpath = (
            str(Path(bpy.path.abspath(str(libpath))).resolve())
        )
        logger.debug(
            "normalized_collection_libpath:\n  %s\nnormalized_libpath:\n  %s",
            normalized_collection_libpath,
            normalized_libpath,
        )
        if normalized_collection_libpath == normalized_libpath:
            logger.info("Library already loaded, not updating...")
            return

        camera = objects[0]

        camera_action = None
        camera_data_action = None

        if camera.animation_data and camera.animation_data.action:
            camera_action = camera.animation_data.action

        if camera.data.animation_data and camera.data.animation_data.action:
            camera_data_action = camera.data.animation_data.action

        actions = (camera_action, camera_data_action)

        self._remove(objects, lib_container)

        objects_list = self._process(
            str(libpath), lib_container, collection.name, actions)

        # Save the list of objects in the metadata container
        collection_metadata["objects"] = objects_list
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
        lib_container = collection_metadata["lib_container"]

        self._remove(objects, lib_container)

        bpy.data.collections.remove(collection)

        return True
