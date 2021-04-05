"""
Requires:
    none

Provides:
    context     -> machine (str)
"""

import pyblish.api


class CollectMachineName(pyblish.api.ContextPlugin):
    label = "Local Machine Name"
    order = pyblish.api.CollectorOrder
    hosts = ["*"]

    def process(self, context):
        import socket

        machine_name = socket.gethostname()
        self.log.info("Machine name: %s" % machine_name)
        context.data["machine"] = machine_name
