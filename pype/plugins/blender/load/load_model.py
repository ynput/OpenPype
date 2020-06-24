"""Load a model asset in Blender."""

import logging
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

from avalon import api, blender
import bpy
import pype.hosts.blender.plugin as plugin

logger = logging.getLogger("pype").getChild("blender").getChild("load_model")


class BlendModelLoader(plugin.AssetLoader):
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

    def _remove(self, objects, container):
        for obj in objects:
            for material_slot in obj.material_slots:
                bpy.data.materials.remove(material_slot.material)
            bpy.data.meshes.remove(obj.data)

        bpy.data.collections.remove(container)

    def prepare_data(self, data, container_name):
        name = data.name
        data = data.make_local()
        data.name = f"{name}:{container_name}"

    def _process(self, libpath, lib_container, container_name):
        relative = bpy.context.preferences.filepaths.use_relative_paths
        with bpy.data.libraries.load(
            libpath, link=True, relative=relative
        ) as (_, data_to):
            data_to.collections = [lib_container]

        scene = bpy.context.scene

        scene.collection.children.link(bpy.data.collections[lib_container])

        model_container = scene.collection.children[lib_container].make_local()
        model_container.name = container_name

        for obj in model_container.objects:
            self.prepare_data(obj, container_name)
            self.prepare_data(obj.data, container_name)

            for material_slot in obj.material_slots:
                self.prepare_data(material_slot.material, container_name)

            if not obj.get(blender.pipeline.AVALON_PROPERTY):
                obj[blender.pipeline.AVALON_PROPERTY] = dict()

            avalon_info = obj[blender.pipeline.AVALON_PROPERTY]
            avalon_info.update({"container_name": container_name})

        model_container.pop(blender.pipeline.AVALON_PROPERTY)

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
        namespace = namespace or plugin.asset_namespace(
            asset, subset
        )
        container_name = plugin.asset_name(
            asset, subset, namespace
        )

        collection = bpy.data.collections.new(lib_container)
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

        obj_container = self._process(
            libpath, lib_container, container_name)

        container_metadata["obj_container"] = obj_container

        # Save the list of objects in the metadata container
        container_metadata["objects"] = obj_container.all_objects

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
        logger.debug(
            "normalized_collection_libpath:\n  %s\nnormalized_libpath:\n  %s",
            normalized_collection_libpath,
            normalized_libpath,
        )
        if normalized_collection_libpath == normalized_libpath:
            logger.info("Library already loaded, not updating...")
            return

        self._remove(objects, obj_container)

        objects_list = self._process(
            str(libpath), lib_container, collection.name)

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
        obj_container = collection_metadata["obj_container"]

        self._remove(objects, obj_container)

        bpy.data.collections.remove(collection)

        return True


class CacheModelLoader(plugin.AssetLoader):
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
            plugin.asset_name(asset, subset, namespace)
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
