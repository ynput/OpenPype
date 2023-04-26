"""Load a rig asset in Blender."""

from pathlib import Path
from typing import List, Tuple

import bpy
from openpype.hosts.blender.api.properties import OpenpypeContainer

from openpype.pipeline import legacy_io, legacy_create
from openpype.pipeline.create import get_legacy_creator_by_name
from openpype.hosts.blender.api import plugin, get_selection
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class RigLoader(plugin.AssetLoader):
    """Load rigs from a .blend file."""

    color = "orange"

    def _apply_options(self, asset_group, options):
        """Apply load options fro asset_group."""

        task = legacy_io.Session.get("AVALON_TASK")
        asset = legacy_io.Session.get("AVALON_ASSET")
        namespace = asset_group.get(AVALON_PROPERTY, {}).get("namespace", "")

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
                data={"dependencies": representation},
            )

        anim_file = options.get("animation_file")
        if isinstance(anim_file, str) and Path(anim_file).is_file():

            bpy.ops.import_scene.fbx(filepath=anim_file, anim_offset=0.0)
            imported = get_selection()

            armature = None
            for obj in asset_group.all_objects:
                if obj.type == "ARMATURE":
                    armature = obj

            if not armature:
                raise Exception(f"Armature not found for {asset_group.name}")

            for obj in imported:
                if obj.type == "ARMATURE":
                    if not armature.animation_data:
                        armature.animation_data_create()
                    armature.animation_data.action = obj.animation_data.action
                    armature.animation_data.action.name = (
                        f"{asset}_{task}:{namespace}_action"
                    )

            for obj in imported:
                bpy.data.objects.remove(obj)

        action = options.get("action")
        if isinstance(action, bpy.types.Action):
            for obj in asset_group.all_objects:
                if obj.type == "ARMATURE":
                    if not armature.animation_data:
                        armature.animation_data_create()
                    armature.animation_data.action = action

        parent = options.get("parent")
        if isinstance(parent, bpy.types.Collection):
            # clear collection parenting
            for collection in bpy.data.collections:
                if asset_group in collection.children.values():
                    collection.children.unlink(asset_group)
            # reparenting with the option value
            plugin.link_to_collection(asset_group, parent)

    def load(self, *args, **kwargs):
        """Override `load` to ensure one action for every loaded rig."""
        container, datablocks = super().load(*args, **kwargs)

        # Ensure loaded rig has action
        asset = legacy_io.Session.get("AVALON_ASSET")
        task = legacy_io.Session.get("AVALON_TASK")
        for armature in [
            obj
            for obj in container.get_datablocks({bpy.types.Object})
            if obj.type == "ARMATURE"
        ]:
            if armature.animation_data is None:
                armature.animation_data_create()

                action_name = armature.name.replace(":", "_")
                armature.animation_data.action = bpy.data.actions.new(
                    f"{asset}_{task}:{action_name}"
                )

        # Clear orphan data
        plugin.orphans_purge()

        return container, datablocks


class LinkRigLoader(RigLoader):
    """Link rigs from a .blend file."""

    families = ["rig"]
    representations = ["blend"]

    label = "Link Rig"
    icon = "link"
    order = 0

    load_type = "LINK"


class AppendRigLoader(RigLoader):
    """Append rigs from a .blend file."""

    families = ["rig"]
    representations = ["blend"]

    label = "Append Rig"
    icon = "paperclip"
    order = 1

    load_type = "APPEND"
