import maya.mel as mel
import pymel.core as pm

import pyblish.api
import openpype.api


def get_file_rule(rule):
    """Workaround for a bug in python with cmds.workspace"""
    return mel.eval('workspace -query -fileRuleEntry "{}"'.format(rule))


class ValidateRenderImageRule(pyblish.api.InstancePlugin):
    """Validates "images" file rule is set to "renders/"

    """

    order = openpype.api.ValidateContentsOrder
    label = "Images File Rule (Workspace)"
    hosts = ["maya"]
    families = ["renderlayer"]
    actions = [openpype.api.RepairAction]

    def process(self, instance):

        default_render_file = self.get_default_render_image_folder(instance)

        assert get_file_rule("images") == default_render_file, (
            "Workspace's `images` file rule must be set to: {}".format(
                default_render_file
            )
        )

    @classmethod
    def repair(cls, instance):
        default = cls.get_default_render_image_folder(instance)
        pm.workspace.fileRules["images"] = default
        pm.system.Workspace.save()

    @staticmethod
    def get_default_render_image_folder(instance):
        return instance.context.data.get('project_settings')\
            .get('maya') \
            .get('create') \
            .get('CreateRender') \
            .get('default_render_image_folder')
