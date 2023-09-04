import pyblish.api
from maya import cmds

from openpype.pipeline.publish import (
    PublishValidationError, RepairAction, ValidateContentsOrder
)


class ValidateRenderImageRule(pyblish.api.InstancePlugin):
    """Validates Maya Workpace "images" file rule matches project settings.

    This validates against the configured default render image folder:
        Studio Settings > Project > Maya >
        Render Settings > Default render image folder.

    """

    order = ValidateContentsOrder
    label = "Images File Rule (Workspace)"
    hosts = ["maya"]
    families = ["renderlayer"]
    actions = [RepairAction]

    required_images_rule = "renders/maya"

    @classmethod
    def apply_settings(cls, project_settings):
        cls.required_images_rule = project_settings["maya"]["RenderSettings"]["default_render_image_folder"]  # noqa

    def process(self, instance):

        required_images_rule = self.required_images_rule
        current_images_rule = cmds.workspace(fileRuleEntry="images")

        if current_images_rule != required_images_rule:
            raise PublishValidationError(
                "Invalid workspace `images` file rule value: '{}'. "
                "Must be set to: '{}'".format(current_images_rule,
                                              required_images_rule)
            )

    @classmethod
    def repair(cls, instance):

        required_images_rule = cls.required_images_rule
        current_images_rule = cmds.workspace(fileRuleEntry="images")

        if current_images_rule != required_images_rule:
            cmds.workspace(fileRule=("images", required_images_rule))
            cmds.workspace(saveWorkspace=True)
