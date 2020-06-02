"""Load a model asset in Blender."""

import logging
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

from avalon import api, blender
import bpy
import pype.hosts.blender.plugin

logger = logging.getLogger("pype").getChild("blender").getChild("load_model")


class BlendModelLoader(pype.hosts.blender.plugin.AssetLoader):
    """Load models from a .blend file.

    Because they come from a .blend file we can simply link the collection that
    contains the model. There is no further need to 'containerise' it.

    Warning:
        Loading the same asset more then once is not properly supported at the
        moment.
    """

    families = ["model"]
    representations = ["blend"]

    label = "Link Model"
    icon = "code-fork"
    color = "orange"

    @staticmethod
    def _remove(self, objects, lib_container):

        for obj in objects:

            bpy.data.meshes.remove(obj.data)

        bpy.data.collections.remove(bpy.data.collections[lib_container])

    @staticmethod
    def _process(self, libpath, lib_container, container_name):

        relative = bpy.context.preferences.filepaths.use_relative_paths
        with bpy.data.libraries.load(
            libpath, link=True, relative=relative
        ) as (_, data_to):
            data_to.collections = [lib_container]

        scene = bpy.context.scene

        scene.collection.children.link(bpy.data.collections[lib_container])

        model_container = scene.collection.children[lib_container].make_local()

        objects_list = []

        for obj in model_container.objects:

            obj = obj.make_local()

            obj.data.make_local()

            for material_slot in obj.material_slots:

                material_slot.material.make_local()

            if not obj.get(blender.pipeline.AVALON_PROPERTY):

                obj[blender.pipeline.AVALON_PROPERTY] = dict()

            avalon_info = obj[blender.pipeline.AVALON_PROPERTY]
            avalon_info.update({"container_name": container_name})

            objects_list.append(obj)

        model_container.pop(blender.pipeline.AVALON_PROPERTY)

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

        collection = bpy.data.collections.new(lib_container)
        collection.name = container_name
        blender.pipeline.containerise_existing(
            collection,
            name,
            namespace,
            context,
            self.__class__.__name__,
        )

        container_metadata = collection.get(
            blender.pipeline.AVALON_PROPERTY)

        container_metadata["libpath"] = libpath
        container_metadata["lib_container"] = lib_container

        objects_list = self._process(
            self, libpath, lib_container, container_name)

        # Save the list of objects in the metadata container
        container_metadata["objects"] = objects_list

        nodes = list(collection.objects)
        nodes.append(collection)
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

        logger.debug(
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

        self._remove(self, objects, lib_container)

        objects_list = self._process(
            self, str(libpath), lib_container, collection.name)

        # Save the list of objects in the metadata container
        collection_metadata["objects"] = objects_list
        collection_metadata["libpath"] = str(libpath)
        collection_metadata["representation"] = str(representation["_id"])

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

        self._remove(self, objects, lib_container)

        bpy.data.collections.remove(collection)

        return True


class CacheModelLoader(pype.hosts.blender.plugin.AssetLoader):
    """Load cache models.

    Stores the imported asset in a collection named after the asset.

    Note:
        At least for now it only supports Alembic files.
    """

    families = ["model"]
    representations = ["abc"]

    label = "Link Model"
    icon = "code-fork"
    color = "orange"

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
        raise NotImplementedError(
            "Loading of Alembic files is not yet implemented.")
        # TODO (jasper): implement Alembic import.

        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]
        # TODO (jasper): evaluate use of namespace which is 'alien' to Blender.
        lib_container = container_name = (
            pype.hosts.blender.plugin.asset_name(asset, subset, namespace)
        )
        relative = bpy.context.preferences.filepaths.use_relative_paths

        with bpy.data.libraries.load(
            libpath, link=True, relative=relative
        ) as (data_from, data_to):
            data_to.collections = [lib_container]

        scene = bpy.context.scene
        instance_empty = bpy.data.objects.new(
            container_name, None
        )
        scene.collection.objects.link(instance_empty)
        instance_empty.instance_type = 'COLLECTION'
        collection = bpy.data.collections[lib_container]
        collection.name = container_name
        instance_empty.instance_collection = collection

        nodes = list(collection.objects)
        nodes.append(collection)
        nodes.append(instance_empty)
        self[:] = nodes
        return nodes
