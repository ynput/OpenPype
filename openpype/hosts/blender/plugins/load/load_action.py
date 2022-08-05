"""Load an action in Blender."""

from typing import Dict

import bpy

from openpype.hosts.blender.api import plugin


class ActionLoader(plugin.AssetLoader):
    """Load action from a .blend file."""

    color = "orange"
    color_tag = "COLOR_07"

    def _get_action(
        self, asset_group: bpy.types.Collection
    ) -> bpy.types.Action:
        """Get action from asset_group collection."""
        for obj in asset_group.objects:
            if obj.animation_data and obj.animation_data.action:
                return obj.animation_data.action

    def _remove_container(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container: Container to remove.

        Returns:
            bool: Whether the container was deleted.
        """
        asset_group = self._get_asset_group_container(container)

        if not asset_group:
            for obj in asset_group.objects:
                if obj.animation_data and obj.animation_data.action:
                    bpy.data.actions.remove(obj.animation_data.action)

        return super()._remove_container(container)

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""

        asset_group = self._get_asset_group_container(container)
        old_action = self._get_action(asset_group) if asset_group else None

        if old_action:
            old_action.name = f"{old_action.name}.old"

        asset_group = self._update_process(container, representation)
        new_action = self._get_action(asset_group) if asset_group else None

        if old_action:
            # replace assigned old_action with new_action.
            if new_action:
                for obj in bpy.data.objects:
                    if (
                        obj.animation_data
                        and obj.animation_data.action is old_action
                    ):
                        obj.animation_data.action = new_action

            bpy.data.actions.remove(old_action)

        return asset_group


class LinkActionLoader(ActionLoader):
    """Link action from a .blend file."""

    families = ["action"]
    representations = ["blend"]

    label = "Link Action"
    icon = "link"
    order = 0

    def _process(self, libpath: str, asset_group: bpy.types.Collection):
        self._link_blend(libpath, asset_group)


class AppendActionLoader(ActionLoader):
    """Append action from a .blend file."""

    families = ["action"]
    representations = ["blend"]

    label = "Append Action"
    icon = "paperclip"
    order = 1

    def _process(self, libpath: str, asset_group: bpy.types.Collection):
        self._append_blend(libpath, asset_group)
