# -*- coding: utf-8 -*-
"""Creator for Unreal Skeletal Meshes."""
from openpype.hosts.maya.api import plugin, lib
from openpype.lib import (
    BoolDef,
    TextDef
)

from maya import cmds  # noqa


class CreateUnrealSkeletalMesh(plugin.MayaCreator):
    """Unreal Static Meshes with collisions."""

    identifier = "io.openpype.creators.maya.unrealskeletalmesh"
    label = "Unreal - Skeletal Mesh"
    family = "skeletalMesh"
    icon = "thumbs-up"
    dynamic_subset_keys = ["asset"]

    # Defined in settings
    joint_hints = set()

    def apply_settings(self, project_settings):
        """Apply project settings to creator"""
        settings = (
            project_settings["maya"]["create"]["CreateUnrealSkeletalMesh"]
        )
        self.joint_hints = set(settings.get("joint_hints", []))

    def get_dynamic_data(
        self, variant, task_name, asset_doc, project_name, host_name, instance
    ):
        """
        The default subset name templates for Unreal include {asset} and thus
        we should pass that along as dynamic data.
        """
        dynamic_data = super(CreateUnrealSkeletalMesh, self).get_dynamic_data(
            variant, task_name, asset_doc, project_name, host_name, instance
        )
        dynamic_data["asset"] = asset_doc["name"]
        return dynamic_data

    def create(self, subset_name, instance_data, pre_create_data):

        with lib.undo_chunk():
            instance = super(CreateUnrealSkeletalMesh, self).create(
                subset_name, instance_data, pre_create_data)
            instance_node = instance.get("instance_node")

            # We reorganize the geometry that was originally added into the
            # set into either 'joints_SET' or 'geometry_SET' based on the
            # joint_hints from project settings
            members = cmds.sets(instance_node, query=True) or []
            cmds.sets(clear=instance_node)

            geometry_set = cmds.sets(name="geometry_SET", empty=True)
            joints_set = cmds.sets(name="joints_SET", empty=True)

            cmds.sets([geometry_set, joints_set], forceElement=instance_node)

            for node in members:
                if node in self.joint_hints:
                    cmds.sets(node, forceElement=joints_set)
                else:
                    cmds.sets(node, forceElement=geometry_set)

    def get_instance_attr_defs(self):

        defs = lib.collect_animation_defs()

        defs.extend([
            BoolDef("renderableOnly",
                    label="Renderable Only",
                    tooltip="Only export renderable visible shapes",
                    default=False),
            BoolDef("visibleOnly",
                    label="Visible Only",
                    tooltip="Only export dag objects visible during "
                            "frame range",
                    default=False),
            BoolDef("includeParentHierarchy",
                    label="Include Parent Hierarchy",
                    tooltip="Whether to include parent hierarchy of nodes in "
                            "the publish instance",
                    default=False),
            BoolDef("worldSpace",
                    label="World-Space Export",
                    default=True),
            BoolDef("refresh",
                    label="Refresh viewport during export",
                    default=False),
            TextDef("attr",
                    label="Custom Attributes",
                    default="",
                    placeholder="attr1, attr2"),
            TextDef("attrPrefix",
                    label="Custom Attributes Prefix",
                    placeholder="prefix1, prefix2")
        ])

        return defs
