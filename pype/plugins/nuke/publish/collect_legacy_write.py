import nuke

import pyblish.api


class CollectWriteLegacy(pyblish.api.ContextPlugin):
    """Collect legacy write nodes."""

    order = pyblish.api.CollectorOrder
    label = "Collect Write Legacy"
    hosts = ["nuke", "nukeassist"]

    def process(self, context):

        for node in nuke.allNodes():
            if node.Class() != "Write":
                continue

            if "avalon" not in node.knobs().keys():
                continue

            instance = context.create_instance(
                node.name(), family="write.legacy"
            )
            instance.append(node)
