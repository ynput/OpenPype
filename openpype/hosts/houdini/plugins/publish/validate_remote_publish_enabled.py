# -*- coding: utf-8 -*-
import pyblish.api

import hou
from openpype.pipeline.publish import RepairContextAction
from openpype.pipeline import PublishValidationError


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
            raise PublishValidationError(
                "Missing REMOTE_PUBLISH node.", title=self.label)

        if node.isBypassed():
            raise PublishValidationError(
                "REMOTE_PUBLISH must not be bypassed.", title=self.label)

    @classmethod
    def repair(cls, context):
        """(Re)create the node if it fails to pass validation."""

        node = hou.node("/out/REMOTE_PUBLISH")
        if not node:
            raise PublishValidationError(
                "Missing REMOTE_PUBLISH node.", title=cls.label)

        cls.log.info("Disabling bypass on /out/REMOTE_PUBLISH")
        node.bypass(False)
