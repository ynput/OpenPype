import pyblish.api
import pype.api
from pype.plugin import contextplugin_should_run

from maya import cmds


class ValidateVRayTranslatorEnabled(pyblish.api.ContextPlugin):

    order = pype.api.ValidateContentsOrder
    label = "VRay Translator Settings"
    families = ["vrayscene"]
    actions = [pype.api.RepairContextAction]

    def process(self, context):

        # Workaround bug pyblish-base#250
        if not contextplugin_should_run(self, context):
            return

        invalid = self.get_invalid(context)
        if invalid:
            raise RuntimeError("Found invalid VRay Translator settings!")

    @classmethod
    def get_invalid(cls, context):

        invalid = False

        # Get vraySettings node
        vray_settings = cmds.ls(type="VRaySettingsNode")
        assert vray_settings, "Please ensure a VRay Settings Node is present"

        node = vray_settings[0]

        if cmds.setAttr("{}.vrscene_render_on".format(node)):
            cls.log.error("Render is enabled, this should be disabled")
            invalid = True

        if not cmds.getAttr("{}.vrscene_on".format(node)):
            cls.log.error("Export vrscene not enabled")
            invalid = True

        if not cmds.getAttr("{}.misc_eachFrameInFile".format(node)):
            cls.log.error("Each Frame in File not enabled")
            invalid = True

        vrscene_filename = cmds.getAttr("{}.vrscene_filename".format(node))
        if vrscene_filename != "vrayscene/<Scene>/<Layer>/<Layer>":
            cls.log.error("Template for file name is wrong")
            invalid = True

        return invalid

    @classmethod
    def repair(cls, context):

        vray_settings = cmds.ls(type="VRaySettingsNode")
        if not vray_settings:
            node = cmds.createNode("VRaySettingsNode")
        else:
            node = vray_settings[0]

        cmds.setAttr("{}.vrscene_render_on".format(node), False)
        cmds.setAttr("{}.vrscene_on".format(node), True)
        cmds.setAttr("{}.misc_eachFrameInFile".format(node), True)
        cmds.setAttr("{}.vrscene_filename".format(node),
                     "vrayscene/<Scene>/<Layer>/<Layer>",
                     type="string")
