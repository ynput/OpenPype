import pyblish.api

import hou
from openpype.pipeline.publish import RepairContextAction


class ValidateRemotePublishEnabled(pyblish.api.ContextPlugin):
    """Validate the remote publish node is *not* bypassed."""

    order = pyblish.api.ValidatorOrder - 0.39
    families = ["*"]
    hosts = ["houdini"]
    targets = ["deadline"]
    label = "Remote Publish ROP enabled"
    actions = [RepairContextAction]

    def process(self, context):

        node = hou.node("/out/REMOTE_PUBLISH")
        if not node:
            raise RuntimeError("Missing REMOTE_PUBLISH node.")

        if node.isBypassed():
            raise RuntimeError("REMOTE_PUBLISH must not be bypassed.")

    @classmethod
    def repair(cls, context):
        """(Re)create the node if it fails to pass validation."""

        node = hou.node("/out/REMOTE_PUBLISH")
        if not node:
            raise RuntimeError("Missing REMOTE_PUBLISH node.")

        cls.log.info("Disabling bypass on /out/REMOTE_PUBLISH")
        node.bypass(False)
