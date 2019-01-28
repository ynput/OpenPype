import maya.mel as mel

import pyblish.api
import pype.api


def get_file_rule(rule):
    """Workaround for a bug in python with cmds.workspace"""
    return mel.eval('workspace -query -fileRuleEntry "{}"'.format(rule))


class ValidateRenderImageRule(pyblish.api.ContextPlugin):
    """Validates "images" file rule is set to "renders/"

    """

    order = pype.api.ValidateContentsOrder
    label = "Images File Rule (Workspace)"
    hosts = ["maya"]
    families = ["renderlayer"]

    def process(self, context):

        assert get_file_rule("images") == "renders", (
            "Workspace's `images` file rule must be set to: renders"
        )
