"""Load a layout in Blender."""

import bpy

from openpype import lib
from openpype.pipeline import legacy_io, legacy_create
from openpype.pipeline.create import get_legacy_creator_by_name
from openpype.hosts.blender.api import plugin


class BlendLayoutLoader(plugin.AssetLoader):
    """Load layout from a .blend file."""

    families = ["layout"]
    representations = ["blend"]

    label = "Link Layout"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_02"

    def _make_local_actions(self, asset_group):
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

    def _create_animation_collection(self, asset_groups, context):
        creator_plugin = get_legacy_creator_by_name("CreateAnimation")
        if not creator_plugin:
            raise ValueError(
                'Creator plugin "CreateAnimation" was not found.'
            )

        legacy_create(
            creator_plugin,
            name="animationMain",
            asset=context["asset"]["name"],
            options={"useSelection": False, "asset_groups": asset_groups},
            data={"dependencies": str(context["representation"]["_id"])}
        )

    def _process(self, libpath, asset_group):
        self._load_blend(libpath, asset_group)

        # Make local action only if task not Lighting.
        if legacy_io.Session.get("AVALON_TASK") != "Lighting":
            self._make_local_actions(asset_group)

    def process_asset(self, context, *args, **kwargs) -> bpy.types.Collection:
        """Asset loading Process"""
        asset_group = super().process_asset(context, *args, **kwargs)

        # Create animation collection subset for loaded rig asset groups.
        if legacy_io.Session.get("AVALON_TASK") == "Animation":
            rig_assets = [
                child
                for child in plugin.get_children_recursive(asset_group)
                if plugin.is_container(child, family="rig")
            ]
            self._create_animation_collection(rig_assets, context)

        plugin.orphans_purge()

        return asset_group
