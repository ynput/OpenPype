import pyblish.api
import nuke


class CollectActiveViewer(pyblish.api.ContextPlugin):
    """Collect any active viewer from nodes
    """

    order = pyblish.api.CollectorOrder + 0.3
    label = "Collect Active Viewer"
    hosts = ["nuke"]

    def process(self, context):
        context.data["ActiveViewer"] = nuke.activeViewer()
