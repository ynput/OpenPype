"""Load an animation in Blender."""

from typing import Dict

import bpy

from openpype.hosts.blender.api import plugin


class AnimationLoader(plugin.AssetLoader):
    """Load animations from a .blend file."""

    color = "orange"
    color_tag = "COLOR_07"

    linked_library = None

    def _load_actions_from_library(self, libpath):
        """Load and link actions from libpath library."""
        with bpy.data.libraries.load(
            libpath, link=self.linked_library, relative=False
        ) as (data_from, data_to):
            data_to.actions = data_from.actions

        return data_to.actions

    def _remove_actions_from_library(self, asset_group):
        """Remove action from all objects in asset_group"""
        for obj in asset_group.all_objects:
            if obj.animation_data and obj.animation_data.action:
                obj.animation_data.action = None

    def _remove_container(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container: Container to remove.

        Returns:
            bool: Whether the container was deleted.
        """
        asset_group = self._get_asset_group_container(container)

        if asset_group:

            # Remove actions from asset_group container.
            self._remove_actions_from_library(asset_group)

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
                    f"invalid collection name '{collection_name}' "
                    f"for action: {action.name}"
                )
                armature = collection.all_objects.get(armature_name)

            assert armature, (
                f"invalid armature name '{armature_name}' "
                f"for action: {action.name}"
            )

            if not armature.animation_data:
                armature.animation_data_create()
            armature.animation_data.action = action

            if collection:
                plugin.link_to_collection(collection, asset_group)
            else:
                plugin.link_to_collection(armature, asset_group)

        plugin.orphans_purge()


class LinkAnimationLoader(AnimationLoader):
    """Link animations from a .blend file."""

    families = ["animation"]
    representations = ["blend"]

    label = "Link Animation"
    icon = "link"
    order = 0

    linked_library = True

    def _remove_actions_from_library(self, asset_group):
        """Restor action from override library reference animation data"""
        for obj in asset_group.all_objects:
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


class AppendAnimationLoader(AnimationLoader):
    """Append animations from a .blend file."""

    families = ["animation"]
    representations = ["blend"]

    label = "Append Animation"
    icon = "paperclip"
    order = 1

    linked_library = False
