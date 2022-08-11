import maya.mel as mel
import pymel.core as pm

import pyblish.api
import openpype.api


def get_file_rule(rule):
    """Workaround for a bug in python with cmds.workspace"""
    return mel.eval('workspace -query -fileRuleEntry "{}"'.format(rule))


class ValidateRenderImageRule(pyblish.api.InstancePlugin):
    """Validates Maya Workpace "images" file rule matches project settings.

    This validates against the configured default render image folder:
        Studio Settings > Project > Maya >
        Render Settings > Default render image folder.

    """

    order = openpype.api.ValidateContentsOrder
    label = "Images File Rule (Workspace)"
    hosts = ["maya"]
    families = ["renderlayer"]
    actions = [openpype.api.RepairAction]

    def process(self, instance):

        required_images_rule = self.get_default_render_image_folder(instance)
        current_images_rule = get_file_rule("images")

        assert current_images_rule == required_images_rule, (
            "Invalid workspace `images` file rule value: '{}'. "
            "Must be set to: '{}'".format(
                current_images_rule, required_images_rule
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
            .get('RenderSettings') \
            .get('default_render_image_folder')
