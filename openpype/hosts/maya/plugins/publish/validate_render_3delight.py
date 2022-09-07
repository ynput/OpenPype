from maya import cmds
import maya.app.renderSetup.model.renderSetup as renderSetup

import pyblish.api
import openpype.api


class ValidateRender3delight(pyblish.api.InstancePlugin):
    """Validates settings needed for 3delight

    """

    order = openpype.api.ValidateContentsOrder
    label = "3delight Rendering Validation"
    hosts = ["maya"]
    families = ["renderlayer"]

    def process(self, instance):

        error = self.has_matching_dl_render_setting(instance)
        if error:
            raise RuntimeError("Missing matching dlRenderSettings for "
                               "'{}' : {}".format(instance.name, error))

        error = self.has_valid_filename(instance)
        if error:
            raise RuntimeError("Incorrect output filename for "
                               "'{}' : {}".format(instance.name, error))

        error = self.invalid_token_in_filename(instance)
        if error:
            raise RuntimeError("Token '{}' not currently supported for "
                               "{}".format(error, instance.name))

    @classmethod
    def has_matching_dl_render_setting(cls, instance):

        if not instance.name.endswith("_RL"):
            return "Wrong suffix (must be '_RL')"

        dl_render_setting_name = instance.name[:-3]
        dl_render_settings = cmds.ls(dl_render_setting_name)
        if len(dl_render_settings) != 1:
            return "Can't find matching dlRenderSettings node"

        return None

    @classmethod
    def has_valid_filename(cls, instance):

        if not instance.name.endswith("_RL"):
            return "Wrong suffix (must be '_RL')"

        dl_render_setting_name = instance.name[:-3]
        dl_render_settings = cmds.ls(dl_render_setting_name)
        if len(dl_render_settings) != 1:
            return "Can't find matching dlRenderSettings node"

        dl_render_setting = dl_render_settings[0]
        fname_attrib = "{}.layerDefaultFilename".format(dl_render_setting)
        fname = cmds.getAttr(fname_attrib)
        if ".#." not in fname:
            return "must contain '.#.' for frame numbering, not '_#.'"

        return None

    @classmethod
    def invalid_token_in_filename(cls, instance):

        if not instance.name.endswith("_RL"):
            return "Wrong suffix (must be '_RL')"

        dl_render_setting_name = instance.name[:-3]
        dl_render_settings = cmds.ls(dl_render_setting_name)
        if len(dl_render_settings) != 1:
            return "Can't find matching dlRenderSettings node"

        dl_render_setting = dl_render_settings[0]
        fname_attrib = "{}.layerDefaultFilename".format(dl_render_setting)
        fname = cmds.getAttr(fname_attrib)
        invalid_tokens = ["<aov>", "<shape_name>"]
        for invalid_token in invalid_tokens:
            if invalid_token in fname:
                return invalid_token

        return None
