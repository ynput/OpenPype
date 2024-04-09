# -*- coding: utf-8 -*-
"""Validate VRay Translator settings."""
import pyblish.api
from openpype.pipeline.publish import (
    context_plugin_should_run,
    RepairContextAction,
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)

from maya import cmds


class ValidateVRayTranslatorEnabled(pyblish.api.ContextPlugin,
                                    OptionalPyblishPluginMixin):
    """Validate VRay Translator settings for extracting vrscenes."""

    order = ValidateContentsOrder
    label = "VRay Translator Settings"
    families = ["vrayscene_layer"]
    actions = [RepairContextAction]
    optional = False

    def process(self, context):
        """Plugin entry point."""
        if not self.is_active(context.data):
            return
        # Workaround bug pyblish-base#250
        if not context_plugin_should_run(self, context):
            return

        invalid = self.get_invalid(context)
        if invalid:
            raise PublishValidationError(
                message="Found invalid VRay Translator settings",
                title=self.label
            )

    @classmethod
    def get_invalid(cls, context):
        """Get invalid instances."""
        invalid = False

        # Get vraySettings node
        vray_settings = cmds.ls(type="VRaySettingsNode")
        if not vray_settings:
            raise PublishValidationError(
                "Please ensure a VRay Settings Node is present",
                title=cls.label
            )

        node = vray_settings[0]

        if cmds.setAttr("{}.vrscene_render_on".format(node)):
            cls.log.error(
                "Render is enabled, for export it should be disabled")
            invalid = True

        if not cmds.getAttr("{}.vrscene_on".format(node)):
            cls.log.error("Export vrscene not enabled")
            invalid = True

        for instance in context:
            if "vrayscene_layer" not in instance.data.get("families"):
                continue

            if instance.data.get("vraySceneMultipleFiles"):
                if not cmds.getAttr("{}.misc_eachFrameInFile".format(node)):
                    cls.log.error("Each Frame in File not enabled")
                    invalid = True
            else:
                if cmds.getAttr("{}.misc_eachFrameInFile".format(node)):
                    cls.log.error("Each Frame in File is enabled")
                    invalid = True

        vrscene_filename = cmds.getAttr("{}.vrscene_filename".format(node))
        if vrscene_filename != "vrayscene/<Scene>/<Layer>/<Layer>":
            cls.log.error("Template for file name is wrong")
            invalid = True

        return invalid

    @classmethod
    def repair(cls, context):
        """Repair invalid settings."""
        vray_settings = cmds.ls(type="VRaySettingsNode")
        if not vray_settings:
            node = cmds.createNode("VRaySettingsNode")
        else:
            node = vray_settings[0]

        cmds.setAttr("{}.vrscene_render_on".format(node), False)
        cmds.setAttr("{}.vrscene_on".format(node), True)
        for instance in context:
            if "vrayscene" not in instance.data.get("families"):
                continue

            if instance.data.get("vraySceneMultipleFiles"):
                cmds.setAttr("{}.misc_eachFrameInFile".format(node), True)
            else:
                cmds.setAttr("{}.misc_eachFrameInFile".format(node), False)
        cmds.setAttr("{}.vrscene_filename".format(node),
                     "vrayscene/<Scene>/<Layer>/<Layer>",
                     type="string")
