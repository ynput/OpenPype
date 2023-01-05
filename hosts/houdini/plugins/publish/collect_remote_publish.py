import pyblish.api
import openpype.api

import hou
from openpype.hosts.houdini.api import lib


class CollectRemotePublishSettings(pyblish.api.ContextPlugin):
    """Collect custom settings of the Remote Publish node."""

    order = pyblish.api.CollectorOrder
    families = ["*"]
    hosts = ["houdini"]
    targets = ["deadline"]
    label = "Remote Publish Submission Settings"
    actions = [openpype.api.RepairAction]

    def process(self, context):

        node = hou.node("/out/REMOTE_PUBLISH")
        if not node:
            return

        attributes = lib.read(node)

        # Debug the settings we have collected
        for key, value in sorted(attributes.items()):
            self.log.debug("Collected %s: %s" % (key, value))

        context.data.update(attributes)
