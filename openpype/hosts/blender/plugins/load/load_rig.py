"""Load a rig asset in Blender."""

from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

import bpy

from avalon import api
from avalon.blender import lib as avalon_lib
from openpype import lib
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import (
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
    AVALON_CONTAINER_ID,
)


class BlendRigLoader(plugin.AssetLoader):
    """Load rigs from a .blend file."""

    families = ["rig"]
    representations = ["blend"]

    label = "Link Rig"
    icon = "code-fork"
    color = "orange"

    def _remove(self, container):
        objects = list(container.objects)
        for obj in objects:
            if obj.type == "MESH":
                for material_slot in list(obj.material_slots):
                    if material_slot.material is not None:
                        if (
                            material_slot.material.library is None
                            and material_slot.material.override_library is None
                        ):
                            bpy.data.materials.remove(material_slot.material)
                if obj.data.library is None and obj.data.override_library is None:
                    bpy.data.meshes.remove(obj.data)
            elif obj.type == "EMPTY":
                objects.extend(obj.objects)
                if obj.library is None and obj.override_library is None:
                    bpy.data.objects.remove(obj)
        bpy.data.collections.remove(container)

    def _process(self, libpath):
        with bpy.data.libraries.load(libpath, link=True, relative=False) as (
            data_from,
            data_to,
        ):
            data_to.collections = data_from.collections

        scene_collection = bpy.context.scene.collection

        # Find the loaded collection and set in variable container_collection
        container_collection = None
        instances = plugin.get_instances_list()
        self.log.info("instances : %s", instances)
        for data_collection in instances:
            if data_collection.override_library is None:
                if data_collection[AVALON_PROPERTY].get("family") is not None:
                    if data_collection[AVALON_PROPERTY].get("family") == "rig":
                        container_collection = data_collection
        self.original_container_name = container_collection.name

        # Create a collection used to start the load collections at .001
        # increment_use_collection = bpy.data.collections.new(
        #     name=self.original_container_name
        # )

        # Link the container to the scene collection
        # scene_collection.children.link(increment_use_collection)
        scene_collection.children.link(container_collection)

        # Get all the collection of the container. The farest parents in first for override them first
        collections = []
        nodes = list(container_collection.children)
        collections.append(container_collection)

        for collection in nodes:
            collections.append(collection)
            nodes.extend(list(collection.children))

        # Get all the object of the container. The farest parents in first for override them first
        objects = []
        armatures = []
        non_armatures = []
        for collection in collections:
            nodes = list(collection.objects)
            objects_of_the_collection = []
            for obj in nodes:
                if obj.parent is None:
                    objects_of_the_collection.append(obj)
            # Get all objects that aren't an armature
            nodes = objects_of_the_collection
            non_armatures = []
            for obj in nodes:
                if obj.type != "ARMATURE":
                    non_armatures.append(obj)
                nodes.extend(list(obj.children))
            non_armatures.reverse()

            # Add them in objects list

            # Get all objects that are an armature
            nodes = objects_of_the_collection

            for obj in nodes:
                if obj.type == "ARMATURE":
                    armatures.append(obj)
                nodes.extend(list(obj.children))
            armatures.reverse()
            # Add them in armature list

        # Clean
        bpy.data.orphans_purge(do_local_ids=False)
        plugin.deselect_all()

        # Override the container and the objects
        for collection in collections:
            container_overrided = collection.override_create(remap_local_usages=True)
        for obj in non_armatures:
            obj.override_create(remap_local_usages=True)
        for armature in armatures:
            armature.override_create(remap_local_usages=True)
        # obj.data.override_create(remap_local_usages=True)

        # Remove the collection used to the increment
        # bpy.data.collections.remove(increment_use_collection)

        return objects

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
        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]
        asset_name = plugin.asset_name(asset, subset)

        objects = self._process(libpath, asset_name)

        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset.

        This will remove all children of the asset group, load the new ones
        and add them as children of the group.
        """
        object_name = container["objectName"]
        avalon_container = bpy.data.collections.get(object_name)
        libpath = Path(api.get_representation_path(representation))

        assert container, f"The asset is not loaded: {container['objectName']}"
        assert libpath, "No existing library file found for {container['objectName']}"
        assert libpath.is_file(), f"The file doesn't exist: {libpath}"

        metadata = avalon_container.get(AVALON_PROPERTY)
        container_libpath = metadata["libpath"]

        normalized_container_libpath = str(
            Path(bpy.path.abspath(container_libpath)).resolve()
        )
        normalized_libpath = str(Path(bpy.path.abspath(str(libpath))).resolve())
        self.log.debug(
            "normalized_group_libpath:\n  %s\nnormalized_libpath:\n  %s",
            normalized_container_libpath,
            normalized_libpath,
        )
        if normalized_container_libpath == normalized_libpath:
            self.log.info("Library already loaded, not updating...")
            return

        # Check how many assets use the same library
        count = 0
        for collection in bpy.data.collections:
            if collection.get(AVALON_PROPERTY) is not None:
                if (
                    collection.override_library is not None
                    and collection.library is None
                ) or (
                    collection.override_library is None and collection.library is None
                ):
                    container_item = collection
                    if (
                        container_item[AVALON_PROPERTY].get("libpath")
                        == container_libpath
                    ):
                        count += 1

        parent_collections = plugin.get_parent_collections(avalon_container)

        if avalon_container.override_library is not None:
            self._remove(avalon_container.override_library.reference)
        self._remove(avalon_container)

        # If it is the last object to use that library, remove it
        print(container_libpath)
        print(bpy.path.basename(container_libpath))
        print(count)
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(container_libpath))
            if library:
                bpy.data.libraries.remove(library)

        container_override = self._process(str(libpath))

        if parent_collections is not None:
            bpy.context.scene.collection.children.unlink(container_override)
            for parent_collection in parent_collections:
                parent_collection.children.link(container_override)

    def exec_remove(self, container: Dict) -> bool:
        """Remove an existing asset group from a Blender scene.

        Arguments:
            container (openpype:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the asset group was deleted.
        """
        object_name = container["objectName"]
        input_container = bpy.data.collections.get(object_name)
        metadata = input_container.get(AVALON_PROPERTY)
        libpath = metadata["libpath"]

        metadata = input_container.get(AVALON_PROPERTY)
        container_libpath = metadata["libpath"]

        normalized_container_libpath = str(
            Path(bpy.path.abspath(container_libpath)).resolve()
        )
        normalized_libpath = str(Path(bpy.path.abspath(str(libpath))).resolve())
        self.log.debug(
            "normalized_group_libpath:\n  %s\nnormalized_libpath:\n  %s",
            normalized_container_libpath,
            normalized_libpath,
        )

        # Check how many assets use the same library
        count = 0
        for collection in bpy.data.collections:
            if collection.get(AVALON_PROPERTY) is not None:
                if (
                    collection.override_library is not None
                    and collection.library is None
                ) or (
                    collection.override_library is None and collection.library is None
                ):
                    container_item = collection
                    if (
                        container_item[AVALON_PROPERTY].get("libpath")
                        == container_libpath
                    ):
                        count += 1

        if input_container.override_library is not None:
            self._remove(input_container.override_library.reference)
        self._remove(input_container)

        # If it is the last object to use that library, remove it
        print(container_libpath)
        print(bpy.path.basename(container_libpath))
        print(count)
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(container_libpath))
            if library:
                bpy.data.libraries.remove(library)

        return True

    def update_avalon_property(self, representation: Dict):

        container_collection = None
        instances = plugin.get_instances_list()
        for data_collection in instances:
            if (
                data_collection.override_library is None
                and data_collection.library is None
            ):
                container_collection = data_collection
        self.log.info("container name %s ", container_collection.name)

        # Set the avalon property with the representation data

        asset = str(representation["context"]["asset"])
        subset = str(representation["context"]["subset"])
        asset_name = plugin.asset_name(asset, subset)

        container_collection[AVALON_PROPERTY] = {
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
            "name": asset,
            "namespace": container_collection.name,
            "loader": str(self.__class__.__name__),
            "representation": str(representation["_id"]),
            "libpath": str(representation["data"]["path"]),
            "asset_name": asset_name,
            "parent": str(representation["parent"]),
            "family": str(representation["context"]["family"]),
            "objectName": container_collection.name,
        }
