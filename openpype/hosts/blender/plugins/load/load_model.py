"""Load a model asset in Blender."""

from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

import bpy

from avalon import api
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import (
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
    AVALON_CONTAINER_ID,
)


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
    namespace = ""
    original_container_name = ""

    def _remove(self, asset_group):
        objects = list(asset_group.children)

        for obj in objects:
            if obj.type == "MESH":
                for material_slot in list(obj.material_slots):
                    bpy.data.materials.remove(material_slot.material)
                bpy.data.meshes.remove(obj.data)
            elif obj.type == "EMPTY":
                objects.extend(obj.children)
                bpy.data.objects.remove(obj)

    def _process(self, libpath):
        """Load the blend library file"""
        with bpy.data.libraries.load(libpath, link=True, relative=False) as (
            data_from,
            data_to,
        ):
            data_to.collections = data_from.collections

        scene_collection = bpy.context.scene.collection

        # Find the loaded collection and set in variable container_collection
        container_collection = None
        instances = plugin.get_instances_list()

        for data_collection in instances:
            if data_collection.override_library is None:
                container_collection = data_collection
        self.original_container_name = container_collection.name

        # Create a collection used to start the load collections at .001
        increment_use_collection = bpy.data.collections.new(
            name=self.original_container_name
        )

        # Link the container to the scene collection
        scene_collection.children.link(increment_use_collection)
        scene_collection.children.link(container_collection)

        # Get all the object of the container. The farest parents in first for override them first
        objects = []
        nodes = list(container_collection.objects)
        children_of_the_collection = []

        for obj in nodes:
            if obj.parent is None:
                children_of_the_collection.append(obj)

        nodes = children_of_the_collection
        for obj in nodes:
            objects.append(obj)
            nodes.extend(list(obj.children))

        objects.reverse()

        # Clean
        bpy.data.orphans_purge(do_local_ids=False)
        plugin.deselect_all()

        # Override the container and the objects
        container_overrided = container_collection.override_create(
            remap_local_usages=True
        )
        for obj in objects:
            obj.override_create(remap_local_usages=True)
            obj.data.override_create(remap_local_usages=True)

        # Remove the collection used to the increment
        bpy.data.collections.remove(increment_use_collection)

        return container_overrided

    def process_asset(
        self,
        context: dict,
        name: str,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None,
    ) -> Optional[List]:
        """
        Arguments:
            name: Use pre-defined name
            namespace: Use pre-defined namespace
            context: Full parenthood of representation to load
            options: Additional settings dictionary
        """

        # Setup variable to construct names
        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]
        asset_name = plugin.asset_name(asset, subset)

        # Process the load of the model
        avalon_container = self._process(libpath)

        # TODO check which data should be on the container custom property
        # avalon_container[AVALON_PROPERTY] = {
        #     "schema": "openpype:container-2.0",
        #     "id": AVALON_CONTAINER_ID,
        #     # "original_container_name": self.original_container_name,
        #     "name": asset_name,
        #     "namespace": self.namespace or "",
        #     "loader": str(self.__class__.__name__),
        #     "representation": str(context["representation"]["_id"]),
        #     "libpath": libpath,
        #     "asset_name": asset_name,
        #     "parent": str(context["representation"]["parent"]),
        #     "family": context["representation"]["context"]["family"],
        #     "objectName": self.namespace,
        # }
        objects = avalon_container.objects
        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset.

        This will remove all objects of the current collection, load the new
        ones and add them to the collection.
        If the objects of the collection are used in another collection they
        will not be removed, only unlinked. Normally this should not be the
        case though.
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)
        libpath = Path(api.get_representation_path(representation))
        extension = libpath.suffix.lower()

        self.log.info(
            "Container: %s\nRepresentation: %s",
            pformat(container, indent=2),
            pformat(representation, indent=2),
        )

        assert asset_group, f"The asset is not loaded: {container['objectName']}"
        assert libpath, "No existing library file found for {container['objectName']}"
        assert libpath.is_file(), f"The file doesn't exist: {libpath}"
        assert extension in plugin.VALID_EXTENSIONS, f"Unsupported file: {libpath}"

        metadata = asset_group.get(AVALON_PROPERTY)
        group_libpath = metadata["libpath"]

        normalized_group_libpath = str(Path(bpy.path.abspath(group_libpath)).resolve())
        normalized_libpath = str(Path(bpy.path.abspath(str(libpath))).resolve())
        self.log.debug(
            "normalized_group_libpath:\n  %s\nnormalized_libpath:\n  %s",
            normalized_group_libpath,
            normalized_libpath,
        )
        if normalized_group_libpath == normalized_libpath:
            self.log.info("Library already loaded, not updating...")
            return

        # Check how many assets use the same library
        count = 0
        for obj in bpy.data.collections.get(AVALON_CONTAINERS).objects:
            if obj.get(AVALON_PROPERTY).get("libpath") == group_libpath:
                count += 1

        mat = asset_group.matrix_basis.copy()

        self._remove(asset_group)

        # If it is the last object to use that library, remove it
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(group_libpath))
            if library:
                bpy.data.libraries.remove(library)

        self._process(str(libpath), asset_group, object_name)

        asset_group.matrix_basis = mat

        metadata["libpath"] = str(libpath)
        metadata["representation"] = str(representation["_id"])
        metadata["parent"] = str(representation["parent"])

    def exec_remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container (openpype:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the container was deleted.
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)
        libpath = asset_group.get(AVALON_PROPERTY).get("libpath")

        # Check how many assets use the same library
        count = 0
        for obj in bpy.data.collections.get(AVALON_CONTAINERS).objects:
            if obj.get(AVALON_PROPERTY).get("libpath") == libpath:
                count += 1

        if not asset_group:
            return False

        self._remove(asset_group)

        bpy.data.objects.remove(asset_group)

        # If it is the last object to use that library, remove it
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(libpath))
            bpy.data.libraries.remove(library)

        return True
