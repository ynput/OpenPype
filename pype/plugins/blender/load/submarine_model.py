"""Load a model asset in Blender."""

import logging
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

import avalon.blender.pipeline
import bpy
import pype.blender
from avalon import api

logger = logging.getLogger("pype").getChild("blender").getChild("load_model")


class BlendModelLoader(pype.blender.AssetLoader):
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
    def _get_lib_collection(name: str, libpath: Path) -> Optional[bpy.types.Collection]:
        """Find the collection(s) with name, loaded from libpath.

        Note:
            It is assumed that only 1 matching collection is found.
        """
        for collection in bpy.data.collections:
            if collection.name != name:
                continue
            if collection.library is None:
                continue
            if not collection.library.filepath:
                continue
            collection_lib_path = str(Path(bpy.path.abspath(collection.library.filepath)).resolve())
            normalized_libpath = str(Path(bpy.path.abspath(str(libpath))).resolve())
            if collection_lib_path == normalized_libpath:
                return collection
        return None

    @staticmethod
    def _collection_contains_object(
        collection: bpy.types.Collection, object: bpy.types.Object
    ) -> bool:
        """Check if the collection contains the object."""
        for obj in collection.objects:
            if obj == object:
                return True
        return False

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
        lib_container = pype.blender.plugin.model_name(asset, subset)
        container_name = pype.blender.plugin.model_name(
            asset, subset, namespace
        )
        relative = bpy.context.preferences.filepaths.use_relative_paths

        with bpy.data.libraries.load(
            libpath, link=True, relative=relative
        ) as (_, data_to):
            data_to.collections = [lib_container]

        scene = bpy.context.scene
        instance_empty = bpy.data.objects.new(
            container_name, None
        )
        if not instance_empty.get("avalon"):
            instance_empty["avalon"] = dict()
        avalon_info = instance_empty["avalon"]
        avalon_info.update({"container_name": container_name})
        scene.collection.objects.link(instance_empty)
        instance_empty.instance_type = 'COLLECTION'
        container = bpy.data.collections[lib_container]
        container.name = container_name
        instance_empty.instance_collection = container
        container.make_local()
        avalon.blender.pipeline.containerise_existing(
            container,
            name,
            namespace,
            context,
            self.__class__.__name__,
        )

        nodes = list(container.objects)
        nodes.append(container)
        nodes.append(instance_empty)
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
        assert extension in pype.blender.plugin.VALID_EXTENSIONS, (
            f"Unsupported file: {libpath}"
        )
        collection_libpath = (
            self._get_library_from_container(collection).filepath
        )
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
        # Let Blender's garbage collection take care of removing the library
        # itself after removing the objects.
        objects_to_remove = set()
        collection_objects = list()
        collection_objects[:] = collection.objects
        for obj in collection_objects:
            # Unlink every object
            collection.objects.unlink(obj)
            remove_obj = True
            for coll in [
                coll for coll in bpy.data.collections
                if coll != collection
            ]:
                if (
                    coll.objects and
                    self._collection_contains_object(coll, obj)
                ):
                    remove_obj = False
            if remove_obj:
                objects_to_remove.add(obj)

        for obj in objects_to_remove:
            # Only delete objects that are not used elsewhere
            bpy.data.objects.remove(obj)

        instance_empties = [
            obj for obj in collection.users_dupli_group
            if obj.name in collection.name
        ]
        if instance_empties:
            instance_empty = instance_empties[0]
            container_name = instance_empty["avalon"]["container_name"]

        relative = bpy.context.preferences.filepaths.use_relative_paths
        with bpy.data.libraries.load(
            str(libpath), link=True, relative=relative
        ) as (_, data_to):
            data_to.collections = [container_name]

        new_collection = self._get_lib_collection(container_name, libpath)
        if new_collection is None:
            raise ValueError(
                "A matching collection '{container_name}' "
                "should have been found in: {libpath}"
            )

        for obj in new_collection.objects:
            collection.objects.link(obj)
        bpy.data.collections.remove(new_collection)
        # Update the representation on the collection
        avalon_prop = collection[avalon.blender.pipeline.AVALON_PROPERTY]
        avalon_prop["representation"] = str(representation["_id"])

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
        instance_parents = list(collection.users_dupli_group)
        instance_objects = list(collection.objects)
        for obj in instance_objects + instance_parents:
            bpy.data.objects.remove(obj)
        bpy.data.collections.remove(collection)

        return True


class CacheModelLoader(pype.blender.AssetLoader):
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
        raise NotImplementedError("Loading of Alembic files is not yet implemented.")
        # TODO (jasper): implement Alembic import.

        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]
        # TODO (jasper): evaluate use of namespace which is 'alien' to Blender.
        lib_container = container_name = (
            pype.blender.plugin.model_name(asset, subset, namespace)
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
