"""Load a layout in Blender."""

from typing import Dict

import bpy

from openpype import lib
from openpype.pipeline import legacy_io, legacy_create, AVALON_CONTAINER_ID
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class BlendLayoutLoader(plugin.AssetLoader):
    """Load layout from a .blend file."""

    families = ["layout"]
    representations = ["blend"]

    label = "Link Layout"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_02"

    @staticmethod
    def _make_local_actions(asset_group):
        """Make local for all actions from objects."""

        task = legacy_io.Session.get("AVALON_TASK")
        asset = legacy_io.Session.get("AVALON_ASSET")

        local_actions = {}

        for obj in asset_group.all_objects:
            if not obj.animation_data or not obj.animation_data.action:
                continue

            # Get local action from linked action.
            linked_action = obj.animation_data.action
            local_action = local_actions.get(linked_action)

            if not linked_action.library:
                continue

            # Make action local if needed.
            if not local_action:
                # Get local action name with namespace from linked action.
                action_name = linked_action.name.split(":")[-1]
                local_name = f"{asset}_{task}:{action_name}"
                # Make local action, rename and upadate local_actions dict.
                local_action = linked_action.make_local()
                local_action.name = local_name
                local_actions[linked_action] = local_action

            # Assign local action.
            obj.animation_data.action = local_action

    @staticmethod
    def _create_animation_collection(asset_group, context):
        creator_plugin = lib.get_creator_by_name("CreateAnimation")
        if not creator_plugin:
            raise ValueError(
                'Creator plugin "CreateAnimation" was not found.'
            )

        legacy_create(
            creator_plugin,
            name=f"{asset_group.name}_animation",
            asset=context["asset"]["name"],
            options={"useSelection": False, "asset_group": asset_group},
            data={"dependencies": str(context["representation"]["_id"])}
        )

    @staticmethod
    def _is_rig_container(collection):
        return (
            collection.get(AVALON_PROPERTY)
            and collection[AVALON_PROPERTY].get("family") == "rig"
            and collection[AVALON_PROPERTY].get("id") == AVALON_CONTAINER_ID
        )

    def _process(self, libpath, asset_group, **kwargs):
        return self._load_blend(libpath, asset_group)

    def process_asset(self, context, *args, **kwargs) -> bpy.types.Collection:
        """Asset loading Process"""
        asset_group = super().process_asset(context, *args, **kwargs)
        asset_group.color_tag = self.color_tag

        self._make_local_actions(asset_group)

        # Create animation collection subset for loaded rig asset group.
        if legacy_io.Session.get("AVALON_TASK") == "Animation":
            for child in asset_group.children_recursive:
                if self._is_rig_container(child):
                    self._create_animation_collection(child, context)

        return asset_group

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""
        asset_group = self._update_process(container, representation)

        # TODO : check animation collections.

        # Ensure all updated actions are local.
        self._make_local_actions(asset_group)

    def exec_remove(self, container) -> bool:
        """Remove the existing container from Blender scene"""
        return self._remove_container(container)
