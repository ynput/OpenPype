"""Load a model asset in Blender."""

import logging
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

from avalon import api, blender
import bpy
import pype.hosts.blender.plugin as plugin


class BlendModelLoader(plugin.AssetLoader):
    """Load models from a .blend file.

    Because they come from a .blend file we can simply link the collection that
    contains the model. There is no further need to 'containerise' it.
    """

    families = ["model"]
    representations = ["blend"]

    label = "Link Model"
    icon = "code-fork"
    color = "orange"

    def _remove(self, objects, container):
        for obj in list(objects):
            for material_slot in list(obj.material_slots):
                bpy.data.materials.remove(material_slot.material)
            bpy.data.meshes.remove(obj.data)

        bpy.data.collections.remove(container)

    def _process(
        self, libpath, lib_container, container_name,
        parent_collection
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

        model_container = parent.children[lib_container].make_local()
        model_container.name = container_name

        for obj in model_container.objects:
            local_obj = plugin.prepare_data(obj, container_name)
            plugin.prepare_data(local_obj.data, container_name)

            for material_slot in local_obj.material_slots:
                plugin.prepare_data(material_slot.material, container_name)

            if not obj.get(blender.pipeline.AVALON_PROPERTY):
                local_obj[blender.pipeline.AVALON_PROPERTY] = dict()

            avalon_info = local_obj[blender.pipeline.AVALON_PROPERTY]
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
            libpath, lib_container, container_name, None)

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

        parent = plugin.get_parent_collection(obj_container)

        self._remove(objects, obj_container)

        obj_container = self._process(
            str(libpath), lib_container, container_name, parent)

        # Save the list of objects in the metadata container
        collection_metadata["obj_container"] = obj_container
        collection_metadata["objects"] = obj_container.all_objects
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

        obj_container = plugin.get_local_collection_with_name(
            collection_metadata["obj_container"].name
        )
        objects = obj_container.all_objects

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
