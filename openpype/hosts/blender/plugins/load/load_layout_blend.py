"""Load a layout in Blender."""

from pathlib import Path
from typing import Dict, List, Optional

import bpy

from avalon import api
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
        instances = plugin.get_containers_list()
        for data_collection in instances:
            if data_collection.override_library is None:
                if data_collection[AVALON_PROPERTY].get("family") is not None:
                    if (
                        data_collection[AVALON_PROPERTY].get("family")
                        == "layout"
                    ):
                        container_collection = data_collection

        self.original_container_name = container_collection.name

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

        # Get all the collections of the container.
        collections = plugin.get_all_collections_in_collection(
            container_collection
        )

        # Get all the objects of the container.
        objects = plugin.get_all_objects_in_collection(container_collection)
        armatures = []
        non_armatures = []

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

        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]
        asset_name = plugin.asset_name(asset, subset)

        avalon_container = self._process(libpath, asset_name)

        # Get all the containers in the scene
        sub_avalon_containers = plugin.get_containers_list()

        # Make local all the action on armature
        for sub_avalon_container in sub_avalon_containers:

            # Check if the container is overridden but not liked
            if (
                sub_avalon_container.override_library
                and sub_avalon_container.library is None
            ):
                # Check if the container has the avalon property
                if sub_avalon_container.get(AVALON_PROPERTY):
                    # Check if the container is a rig
                    if sub_avalon_container["avalon"].get("family") == "rig":
                        # Get all the object in the container
                        objects = sub_avalon_container.objects
                        # Get the armatures
                        armatures = [
                            obj for obj in objects if obj.type == "ARMATURE"
                        ]
                        for armature in armatures:
                            # Make local the action
                            if (
                                armature.animation_data
                                and armature.animation_data.action
                            ):
                                armature.animation_data.action.make_local()

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
        avalon_container = bpy.data.collections.get(object_name)
        libpath = Path(api.get_representation_path(representation))

        assert container, f"The asset is not loaded: {container['objectName']}"
        assert (
            libpath
        ), "No existing library file found for {container['objectName']}"
        assert libpath.is_file(), f"The file doesn't exist: {libpath}"

        metadata = avalon_container.get(AVALON_PROPERTY)
        container_libpath = metadata["libpath"]

        normalized_container_libpath = str(
            Path(bpy.path.abspath(container_libpath)).resolve()
        )
        normalized_libpath = str(
            Path(bpy.path.abspath(str(libpath))).resolve()
        )
        self.log.debug(
            f"normalized_group_libpath:\n  '{normalized_container_libpath}'"
            f"\nnormalized_libpath:\n  '{normalized_libpath}'"
        )
        if normalized_container_libpath == normalized_libpath:
            self.log.info("Library already loaded, not updating...")
            return

        # Set temp namespace to avoid object renames while the update
        plugin.set_temp_namespace_for_objects_container(avalon_container)

        parent_collections = plugin.get_parent_collections(avalon_container)

        # Save the animation before we remove the containers
        action = dict()

        # Get all the containers in the scene
        sub_avalon_containers = plugin.get_containers_list()

        # Loop on all containers
        for sub_avalon_container in sub_avalon_containers:
            # Check if the container is overridden but not liked
            if (
                sub_avalon_container.override_library
                and sub_avalon_container.library is None
            ):
                # Check if the container has the avalon property
                if sub_avalon_container.get(AVALON_PROPERTY):
                    # Check if the container is a rig
                    if sub_avalon_container["avalon"].get("family") == "rig":
                        # Get all the object in the container
                        objects = plugin.get_all_objects_in_collection(
                            sub_avalon_container
                        )
                        # Get the armatures
                        armatures = [
                            obj for obj in objects if obj.type == "ARMATURE"
                        ]
                        # Get the action in the animation data
                        for armature in armatures:
                            if (
                                armature.animation_data
                                and armature.animation_data.action
                            ):
                                action[
                                    sub_avalon_container.name
                                ] = armature.animation_data.action
                                armature.animation_data.action.use_fake_user = (
                                    True
                                )

        # Remove the current container
        self._remove(avalon_container)

        # Load the updated container
        container_override = self._process(str(libpath), object_name)

        # Set temp namespace to avoid object renames while the update
        plugin.set_temp_namespace_for_objects_container(container_override)

        # Link the the updated container to the collection of the old container
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

        # Clean the datablocks
        plugin.remove_orphan_datablocks()

        # Load the animation on the containers

        # Get all the containers in the scene
        sub_avalon_containers = plugin.get_containers_list()

        # Loop on all containers
        for sub_avalon_container in sub_avalon_containers:
            # Check if the container is overridden but not liked
            if (
                sub_avalon_container.override_library
                and sub_avalon_container.library is None
            ):
                # Check if the container has the avalon property
                if sub_avalon_container.get(AVALON_PROPERTY):
                    # Check if the container is a rig
                    if sub_avalon_container["avalon"].get("family") == "rig":
                        # Get all the object in the container
                        objects = plugin.get_all_objects_in_collection(
                            sub_avalon_container
                        )
                        # Get the armatures
                        armatures = [
                            obj for obj in objects if obj.type == "ARMATURE"
                        ]
                        for armature in armatures:
                            if armature.animation_data is None:
                                armature.animation_data_create()
                            if action.get(sub_avalon_container.name):
                                # Clear the old animation data
                                armature.animation_data_clear()
                                # Create a new animation data
                                armature.animation_data_create()
                                # Set the action store in the action
                                # variable to the animation data
                                armature.animation_data.action = action[
                                    sub_avalon_container.name
                                ]
                                armature.animation_data.action.use_fake_user = (
                                    False
                                )

        has_namespace = api.Session["AVALON_TASK"] not in [
            "Rigging",
            "Modeling",
        ]
        # Set the name of the objects by its original name and its namespace
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
