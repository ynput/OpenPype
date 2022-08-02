"""Load an action in Blender."""

from typing import Dict

import bpy
import openpype.hosts.blender.api.plugin


class BlendActionLoader(openpype.hosts.blender.api.plugin.AssetLoader):
    """Load action from a .blend file.

    Warning:
        Loading the same asset more then once is not properly supported at the
        moment.
    """

    families = ["action"]
    representations = ["blend"]

    label = "Link Action"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_01"

    def _get_action(
        self, asset_group: bpy.types.Collection
    ) -> bpy.types.Action:
        for obj in asset_group.objects:
            if obj.animation_data and obj.animation_data.action:
                return obj.animation_data.action

    def _process(self, libpath: str, asset_group: bpy.types.Collection):
        self._link_blend(libpath, asset_group)

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""

        object_name = container["objectName"]
        asset_group = bpy.data.collections.get(object_name)

        old_action = None
        if asset_group:
            old_action = self._get_action(asset_group)

        assert old_action, f"No action found for: {object_name}"

        old_action.name = f"{old_action.name}.old"

        asset_group = self._update_process(container, representation)

        new_action = self._get_action(asset_group)

        for obj in bpy.data.objects:
            if obj.animation_data and obj.animation_data.action == old_action:
                obj.animation_data.action = new_action

        bpy.data.actions.remove(old_action)

    def exec_remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene."""

        object_name = container["objectName"]
        asset_group = bpy.data.collections.get(object_name)
        if asset_group:
            action = self._get_action(asset_group)
            if action:
                bpy.data.actions.remove(action)

        return super().exec_remove(container)
