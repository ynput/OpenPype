"""Load an asset in Blender from an Alembic file."""

import logging
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

from avalon import api, blender
import bpy
import openpype.hosts.blender.api.plugin as plugin


class CacheModelLoader(plugin.AssetLoader):
    """Load cache models.

    Stores the imported asset in a collection named after the asset.

    Note:
        At least for now it only supports Alembic files.
    """

    families = ["model", "pointcache"]
    representations = ["abc"]

    label = "Link Alembic"
    icon = "code-fork"
    color = "orange"

    def _remove(self, objects, container):
        for obj in list(objects):
            if obj.type == 'MESH':
                bpy.data.meshes.remove(obj.data)
            elif obj.type == 'EMPTY':
                bpy.data.objects.remove(obj)

        bpy.data.collections.remove(container)

    def _process(self, libpath, container_name, parent_collection):
        bpy.ops.object.select_all(action='DESELECT')

        view_layer = bpy.context.view_layer
        view_layer_collection = view_layer.active_layer_collection.collection

        relative = bpy.context.preferences.filepaths.use_relative_paths
        bpy.ops.wm.alembic_import(
            filepath=libpath,
            relative_path=relative
        )

        parent = parent_collection

        if parent is None:
            parent = bpy.context.scene.collection

        model_container = bpy.data.collections.new(container_name)
        parent.children.link(model_container)
        for obj in bpy.context.selected_objects:
            model_container.objects.link(obj)
            view_layer_collection.objects.unlink(obj)

            name = obj.name
            obj.name = f"{name}:{container_name}"

            # Groups are imported as Empty objects in Blender
            if obj.type == 'MESH':
                data_name = obj.data.name
                obj.data.name = f"{data_name}:{container_name}"

            if not obj.get(blender.pipeline.AVALON_PROPERTY):
                obj[blender.pipeline.AVALON_PROPERTY] = dict()

            avalon_info = obj[blender.pipeline.AVALON_PROPERTY]
            avalon_info.update({"container_name": container_name})

        bpy.ops.object.select_all(action='DESELECT')

        return model_container

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
            libpath, container_name, None)

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

        parent = plugin.get_parent_collection(obj_container)

        self._remove(objects, obj_container)

        obj_container = self._process(
            str(libpath), container_name, parent)

        collection_metadata["obj_container"] = obj_container
        collection_metadata["objects"] = obj_container.all_objects
        collection_metadata["libpath"] = str(libpath)
        collection_metadata["representation"] = str(representation["_id"])

    def remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container (openpype:container-1.0): Container to remove,
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