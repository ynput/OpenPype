"""Load a layout in Blender."""

from typing import Dict, List, Optional

import re
import bpy

from openpype.pipeline import legacy_io
from openpype.hosts.blender.api import plugin


class BlendLayoutLoader(plugin.AssetLoader):
    """Load layout from a .blend file."""

    families = ["layout"]
    representations = ["blend"]

    label = "Link Layout"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_02"

    @staticmethod
    def _make_local_actions(objects):
        """Make local for all actions from objects."""
        # Try to use session task to rename local action.
        session_task = legacy_io.Session.get("AVALON_TASK", "Local")
        local_actions = {}

        for obj in objects:
            if not obj.animation_data or not obj.animation_data.action:
                continue

            # Get local action from linked action.
            linked_action = obj.animation_data.action
            local_action = local_actions.get(linked_action)

            # Make action local if needed.
            if not local_action:
                # Get local action name from linked action name.
                if re.match("*_action[^_]+$", linked_action.name):
                    local_name = re.sub(
                        "*_(action[^_]+)$",
                        linked_action.name,
                        f"_action{session_task}"
                    )
                else:
                    local_name = linked_action.name + f"_action{session_task}"
                # Make local action, rename and upadate local_actions dict.
                local_action = linked_action.make_local()
                local_action.name = local_name
                local_actions[linked_action] = local_action

            # Assign local action.
            obj.animation_data.action = local_action

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

        asset_name = plugin.asset_name(asset, subset)

        asset_group = bpy.data.collections.new(asset_name)
        asset_group.color_tag = self.color_tag
        plugin.get_main_collection().children.link(asset_group)

        objects = self._load_blend(libpath, asset_group)

        self._make_local_actions(objects)

        self._update_metadata(
            asset_group, context, name, namespace, asset_name, libpath
        )

        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""
        self._update_blend(container, representation)

    def exec_remove(self, container) -> bool:
        """Remove the existing container from Blender scene"""
        return self._remove_container(container)
