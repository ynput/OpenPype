"""Load a rig asset in Blender."""

from pathlib import Path
from typing import Dict, List, Optional

import bpy
from avalon import api
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import (
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
        """Remove the container and used data"""
        plugin.remove_container(container)

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
        containers = plugin.get_containers_list()
        for container in containers:
            if container.override_library is None:
                if container[AVALON_PROPERTY].get("family"):
                    if container[AVALON_PROPERTY].get("family") == "rig":
                        if (
                            container[AVALON_PROPERTY].get("asset_name")
                            == asset_name
                        ):
                            container_collection = container

        # Link the container collection to the scene collection
        # or if there is one collection in scene_collection choose
        # this collection
        is_pyblish_container = plugin.is_pyblish_avalon_container(
            scene_collection.children[0]
        )
        if len(scene_collection.children) == 1 and not is_pyblish_container:
            # we don't want to add an asset in another publish container
            plugin.link_collection_to_collection(
                container_collection, scene_collection.children[0]
            )
        else:
            plugin.link_collection_to_collection(
                container_collection, scene_collection
            )

        # Get all the collection of the container. The farest parents in first
        # for override them first

        # Get all the object of the container. The farest parents in first
        # for override them first
        armatures = []
        non_armatures = []
        collections = plugin.get_all_collections_in_collection(
            container_collection
        )
        objects = plugin.get_all_objects_in_collection(container_collection)

        # Get all objects that aren't an armature
        for object in objects:
            if object.type != "ARMATURE":
                non_armatures.append(object)
        non_armatures.reverse()

        # Get all objects that are an armature
        for object in objects:
            if object.type == "ARMATURE":
                armatures.append(object)
        armatures.reverse()

        # Clean
        bpy.data.orphans_purge(do_local_ids=False)
        plugin.deselect_all()
        # Override the container and the objects
        container_overridden = container_collection.override_create(
            remap_local_usages=True
        )

        for collection in collections:
            collection.override_create(remap_local_usages=True)
        for object in non_armatures:
            object.override_create(remap_local_usages=True)

        for armature in armatures:
            armature.override_create(remap_local_usages=True)

        return container_overridden

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

        # Process the load of the container
        avalon_container = self._process(libpath, asset_name)
        has_namespace = api.Session["AVALON_TASK"] not in [
            "Rigging",
            "Modeling",
        ]
        plugin.set_original_name_for_objects_container(
            avalon_container, has_namespace
        )

        objects = avalon_container.objects
        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset.

        This will remove all children of the asset group, load the new ones
        and add them as children of the group.
        """
        # Setup variable to construct names
        object_name = container["objectName"]
        asset_name = container["asset_name"]
        # Get the avalon_container with the object name
        avalon_container = bpy.data.collections.get(object_name)
        # Find the library path in the scene
        libpath = Path(api.get_representation_path(representation))

        assert container, f"The asset is not loaded: {container['objectName']}"
        assert (
            libpath
        ), "No existing library file found for {container['objectName']}"
        assert libpath.is_file(), f"The file doesn't exist: {libpath}"
        # Get the metadata in the container
        metadata = avalon_container.get(AVALON_PROPERTY)
        # Get the library path store in the metadata
        container_libpath = metadata["libpath"]

        normalized_container_libpath = str(
            Path(bpy.path.abspath(container_libpath)).resolve()
        )
        normalized_libpath = str(
            Path(bpy.path.abspath(str(libpath))).resolve()
        )
        self.log.debug(
            f"normalized_group_libpath:\n  {normalized_container_libpath}"
            f"\nnormalized_libpath:\n  {normalized_libpath}"
        )
        # If library exits do nothing
        if normalized_container_libpath == normalized_libpath:
            self.log.info("Library already loaded, not updating...")
            return

        plugin.set_temp_namespace_for_objects_container(avalon_container)

        # Get the parent collections of the container to relink after update
        parent_collections = plugin.get_parent_collections(avalon_container)

        # Get the armature of the rig
        objects = avalon_container.objects
        armature = [obj for obj in objects if obj.type == "ARMATURE"][0]
        # Get the action on the armature
        action = None
        if armature.animation_data and armature.animation_data.action:
            action = armature.animation_data.action
            armature.animation_data.action.use_fake_user = True
        # Remove the container
        self._remove(avalon_container)
        # Clean

        # Load the updated container
        container_override = self._process(str(libpath), asset_name)

        plugin.set_temp_namespace_for_objects_container(container_override)

        # Get the armature of the rig
        objects = container_override.objects
        armature = [obj for obj in objects if obj.type == "ARMATURE"][0]
        # Create the animation_data if doesn't exist
        if armature.animation_data is None:
            armature.animation_data_create()
        # Set the action on the armature
        if armature.animation_data:
            armature.animation_data.action = action
            try:
                action.use_fake_user = False
            except Exception as e:
                print("Remove Fake User Failed", e)
        # Relink the container on the good collection
        if parent_collections:
            if (
                container_override
                in bpy.context.scene.collection.children.values()
            ):
                bpy.context.scene.collection.children.unlink(
                    container_override
                )
            for parent_collection in parent_collections:
                plugin.link_collection_to_collection(
                    container_override, parent_collection
                )

        has_namespace = api.Session["AVALON_TASK"] not in [
            "Rigging",
            "Modeling",
        ]
        plugin.set_original_name_for_objects_container(
            container_override, has_namespace
        )

        # Clean
        plugin.remove_orphan_datablocks()

    def exec_remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container (openpype:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the container was deleted.
        """
        # Setup variable to construct names
        object_name = container["objectName"]
        # Get the avalon_container with the object name
        avalon_container = bpy.data.collections.get(object_name)

        # Remove the container
        self._remove(avalon_container)

        return True

    def update_avalon_property(self, representation: Dict):
        """Set the avalon property with the representation data"""

        # Set the avalon property with the representation data
        asset = str(representation["context"]["asset"])
        subset = str(representation["context"]["subset"])
        asset_name = plugin.asset_name(asset, subset)

        # Get the container in the scene
        container = bpy.data.collections.get(asset_name)

        container_collection = None
        if container.override_library is None and container.library is None:
            # Check if the container isn't publish
            if container["avalon"].get("id") == "pyblish.avalon.instance":
                container_collection = container

        if container_collection:
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
