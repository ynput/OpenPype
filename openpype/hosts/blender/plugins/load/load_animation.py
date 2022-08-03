"""Load an animation in Blender."""

from typing import Dict

import bpy

from openpype.hosts.blender.api import plugin


class LinkAnimationLoader(plugin.AssetLoader):
    """Link animations from a .blend file.

    Warning:
        Loading the same asset more then once is not properly supported at the
        moment.
    """

    families = ["animation"]
    representations = ["blend"]

    label = "Link Animation"
    icon = "link"
    color = "orange"
    color_tag = "COLOR_01"
    order = 0

    def _restor_actions_from_library(self, objects):
        """Restor action from override library reference animation data"""
        for obj in objects:
            if (
                obj.animation_data
                and obj.override_library
                and obj.override_library.reference
                and obj.override_library.reference.animation_data
                and obj.override_library.reference.animation_data.action
            ):
                obj.animation_data.action = (
                    obj.override_library.reference.animation_data.action
                )

    def _load_actions_from_library(self, libpath):
        """Load and link actions from libpath library."""
        with bpy.data.libraries.load(
            libpath, link=True, relative=False
        ) as (data_from, data_to):
            data_to.actions = data_from.actions

        return data_to.actions

    def _remove_container(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container: Container to remove.

        Returns:
            bool: Whether the container was deleted.
        """
        asset_group = self._get_asset_group_container(container)

        if asset_group:

            # Restor action from override library reference animation data.
            self._restor_actions_from_library(asset_group.all_objects)

            # Unlink all child objects and collections.
            for obj in asset_group.objects:
                asset_group.objects.unlink(obj)
            for child in asset_group.children:
                asset_group.children.unlink(child)

        return super()._remove_container(container)

    def _process(self, libpath: str, asset_group: bpy.types.Collection):

        scene = bpy.context.scene
        scene_collections = plugin.get_children_recursive(scene.collection)
        actions = self._load_actions_from_library(libpath)

        assert actions, "No actions found"

        # Try to assign linked actions with parsing their name.
        for action in actions:

            collection_name = action.get("collection", "NONE")
            armature_name = action.get("armature", "NONE")

            collection = next(
                (c for c in scene_collections if c.name == collection_name),
                None
            )

            if collection_name == "NONE":
                armature = bpy.context.scene.objects.get(armature_name)
            else:
                assert collection, (
                    f"invalid collection name for action: {action.name}"
                )
                armature = collection.all_objects.get(armature_name)

            assert armature, (
                f"invalid armature name for action: {armature.name}"
            )

            if not armature.animation_data:
                armature.animation_data_create()
            armature.animation_data.action = action

            if collection:
                plugin.link_to_collection(collection, asset_group)
            else:
                plugin.link_to_collection(armature, asset_group)

        plugin.orphans_purge()


class AppendAnimationLoader(plugin.AssetLoader):
    """Append animations from a .blend file."""

    label = "Append Animation"
    icon = "paperclip"
    order = 1

    def _load_actions_from_library(self, libpath):
        """Load and append actions from libpath library."""
        with bpy.data.libraries.load(
            libpath, link=False, relative=False
        ) as (data_from, data_to):
            data_to.actions = data_from.actions

        return data_to.actions
