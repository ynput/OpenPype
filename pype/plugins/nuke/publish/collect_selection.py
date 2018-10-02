import nuke

import pyblish.api


class CollectSelection(pyblish.api.ContextPlugin):
    """Collect selection."""

    order = pyblish.api.CollectorOrder
    label = "Collect Selection of Nodes"
    hosts = ["nuke"]

    def process(self, context):
        context.data["selection"] = nuke.selectedNodes()
