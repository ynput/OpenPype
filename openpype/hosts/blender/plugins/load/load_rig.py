"""Load a rig asset in Blender."""

from pathlib import Path
from typing import Dict, Optional

import bpy

from openpype import lib
from openpype.pipeline import legacy_io, legacy_create
from openpype.hosts.blender.api import plugin, get_selection
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class BlendRigLoader(plugin.AssetLoader):
    """Load rigs from a .blend file."""

    families = ["rig"]
    representations = ["blend"]

    label = "Link Rig"
    icon = "link"
    color = "orange"
    color_tag = "COLOR_03"

    def _assign_actions(self, asset_group):
        """Assign new action for all objects from linked rig."""

        task = legacy_io.Session.get("AVALON_TASK")
        asset = legacy_io.Session.get("AVALON_ASSET")
        namespace = asset_group.get(AVALON_PROPERTY, {}).get("namespace", "")

        # If rig contain only one armature.
        armatures = [
            obj
            for obj in asset_group.all_objects
            if obj.type == "ARMATURE"
        ]
        if len(armatures) == 1:
            armature = armatures[0]
            if armature.animation_data is None:
                armature.animation_data_create()
                armature.animation_data.action = bpy.data.actions.new(
                    f"{asset}_{task}:{namespace}_action"
                )

        # If rig contain multiple armatures, we generate actions for
        # each armature.
        elif armatures:
            for armature in armatures:
                if armature.animation_data is None:
                    armature.animation_data_create()
                    action_name = armature.name.replace(":", "_")
                    armature.animation_data.action = bpy.data.actions.new(
                        f"{asset}_{task}:{namespace}_{action_name}_action"
                    )

        # If rig contain no armature we generate actions for each object.
        else:
            for obj in asset_group.all_objects:
                if obj.animation_data is None:
                    obj.animation_data_create()
                    action_name = obj.name.replace(":", "_")
                    obj.animation_data.action = bpy.data.actions.new(
                        f"{asset}_{task}:{namespace}_{action_name}_action"
                    )
        plugin.orphans_purge()

    def _apply_options(self, asset_group, options, namespace):
        """Apply load options fro asset_group."""

        task = legacy_io.Session.get("AVALON_TASK")
        asset = legacy_io.Session.get("AVALON_ASSET")

        if options.get("create_animation"):
            creator_plugin = get_legacy_creator_by_name("CreateAnimation")
            if not creator_plugin:
                raise ValueError(
                    'Creator plugin "CreateAnimation" was not found.'
                )

            context = options.get("create_context")
            representation = str(context["representation"]["_id"])

            legacy_create(
                creator_plugin,
                name=f"{namespace}_animation",
                asset=context["asset"]["name"],
                options={"useSelection": False, "asset_group": asset_group},
                data={"dependencies": representation}
            )

        anim_file = options.get('animation_file')
        if isinstance(anim_file, str) and Path(anim_file).is_file():

            bpy.ops.import_scene.fbx(filepath=anim_file, anim_offset=0.0)
            imported = get_selection()

            armature = None
            for obj in asset_group.all_objects:
                if obj.type == 'ARMATURE':
                    armature = obj

            if not armature:
                raise Exception(f"Armature not found for {asset_group.name}")

            for obj in imported:
                if obj.type == 'ARMATURE':
                    if not armature.animation_data:
                        armature.animation_data_create()
                    armature.animation_data.action = obj.animation_data.action
                    armature.animation_data.action.name = (
                        f"{asset}_{task}:{namespace}_action"
                    )

            for obj in imported:
                bpy.data.objects.remove(obj)

        action = options.get('action')
        if isinstance(action, bpy.types.Action):
            for obj in asset_group.all_objects:
                if obj.type == 'ARMATURE':
                    if not armature.animation_data:
                        armature.animation_data_create()
                    armature.animation_data.action = action

        parent = options.get('parent')
        if isinstance(parent, bpy.types.Collection):
            # clear collection parenting
            for collection in bpy.data.collections:
                if asset_group in collection.children.values():
                    collection.children.unlink(asset_group)
            # reparenting with the option value
            plugin.link_to_collection(asset_group, parent)

    def _process(self, libpath, asset_group):
        # Load blend from from libpath library.
        self._link_blend(libpath, asset_group)

        # Disable selection for modeling container.
        for child in set(plugin.get_children_recursive(asset_group)):
            if plugin.is_container(child, family="model"):
                child.hide_select = True

        return asset_group

    def process_asset(
        self,
        context: dict,
        name: str,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> bpy.types.Collection:
        """Asset loading Process"""
        asset_group = super().process_asset(context, name, namespace)

        self._assign_actions(asset_group)

        if options is not None:
            self._apply_options(asset_group, options, namespace)

        return asset_group

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""
        asset_group = self._update_process(container, representation)

        # Ensure updated rig has action.
        self._assign_actions(asset_group)
