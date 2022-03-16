"""Load a layout in Blender."""

from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

import bpy

from avalon import api
from openpype import lib
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import (
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
    AVALON_CONTAINER_ID,
)


class BlendLayoutLoader(plugin.AssetLoader):
    """Load layout from a .blend file."""

    families = ["layout"]
    representations = ["blend"]

    label = "Link Layout"
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

    def _remove_asset_and_library(self, asset_group):
        libpath = asset_group.get(AVALON_PROPERTY).get("libpath")

        # Check how many assets use the same library
        count = 0
        for obj in bpy.data.collections.get(AVALON_CONTAINERS).all_objects:
            if obj.get(AVALON_PROPERTY).get("libpath") == libpath:
                count += 1

        self._remove(asset_group)

        bpy.data.objects.remove(asset_group)

        # If it is the last object to use that library, remove it
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(libpath))
            bpy.data.libraries.remove(library)

    def _process(self, libpath, asset_name):
        with bpy.data.libraries.load(libpath, link=True, relative=False) as (
            data_from,
            data_to,
        ):
            for data_from_collection in data_from.collections:
                if data_from_collection == asset_name:
                    data_to.collections.append(data_from_collection)

        scene_collection = bpy.context.scene.collection

        # Find the loaded collection and set in variable container_collection
        container_collection = None
        instances = plugin.get_instances_list()
        self.log.info("instances : %s", instances)
        for data_collection in instances:
            if data_collection.override_library is None:
                if data_collection[AVALON_PROPERTY].get("family") is not None:
                    if data_collection[AVALON_PROPERTY].get("family") == "layout":
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

        actions = {}

        for obj in asset_group.children:
            obj_meta = obj.get(AVALON_PROPERTY)
            if obj_meta.get("family") == "rig":
                rig = None
                for child in obj.children:
                    if child.type == "ARMATURE":
                        rig = child
                        break
                if not rig:
                    raise Exception("No armature in the rig asset group.")
                if rig.animation_data and rig.animation_data.action:
                    instance_name = obj_meta.get("instance_name")
                    actions[instance_name] = rig.animation_data.action

        mat = asset_group.matrix_basis.copy()

        # Remove the children of the asset_group first
        for child in list(asset_group.children):
            self._remove_asset_and_library(child)

        # Check how many assets use the same library
        count = 0
        for obj in bpy.data.collections.get(AVALON_CONTAINERS).objects:
            if obj.get(AVALON_PROPERTY).get("libpath") == group_libpath:
                count += 1

        self._remove(asset_group)

        # If it is the last object to use that library, remove it
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(group_libpath))
            bpy.data.libraries.remove(library)

        self._process(str(libpath), asset_group, object_name, actions)

        avalon_container = bpy.data.collections.get(AVALON_CONTAINERS)
        for child in asset_group.children:
            if child.get(AVALON_PROPERTY):
                avalon_container.objects.link(child)

        asset_group.matrix_basis = mat

        metadata["libpath"] = str(libpath)
        metadata["representation"] = str(representation["_id"])

    def exec_remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container (openpype:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the container was deleted.

        Warning:
            No nested collections are supported at the moment!
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)

        if not asset_group:
            return False

        # Remove the children of the asset_group first
        for child in list(asset_group.children):
            self._remove_asset_and_library(child)

        self._remove_asset_and_library(asset_group)

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
