import pyblish.api
import colorbleed.api

from maya import cmds


class ValidateVRayTranslatorEnabled(pyblish.api.ContextPlugin):

    order = colorbleed.api.ValidateContentsOrder
    label = "VRay Translator Settings"
    families = ["colorbleed.vrayscene"]
    actions = [colorbleed.api.RepairContextAction]

    def process(self, context):

        # Get vraySettings node
        vray_settings = cmds.ls(type="VRaySettingsNode")
        assert vray_settings, "Please ensure a VRay Settings Node is present"

        node = vray_settings[0]

        if not cmds.getAttr("{}.vrscene_on".format(node)):
            self.info.error("Export vrscene not enabled")

        if not cmds.getAttr("{}.misc_eachFrameInFile".format(node)):
            self.info.error("Each Frame in File not enabled")

        vrscene_filename = cmds.getAttr("{}.vrscene_filename".format(node))
        if vrscene_filename != "vrayscene/<Scene>/<Scene>_<Layer>/<Layer>":
            self.info.error("Template for file name is wrong")

    @classmethod
    def repair(cls, context):

        vray_settings = cmds.ls(type="VRaySettingsNode")
        if not vray_settings:
            node = cmds.createNode("VRaySettingsNode")
        else:
            node = vray_settings[0]

        cmds.setAttr("{}.vrscene_on".format(node), True)
        cmds.setAttr("{}.misc_eachFrameInFile".format(node), True)
        cmds.setAttr("{}.vrscene_filename".format(node),
                     "vrayscene/<Scene>/<Scene>_<Layer>/<Layer>",
                     type="string")
