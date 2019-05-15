from pyblish import api

class CollectFramerate(api.ContextPlugin):
    """Collect framerate from selected sequence."""

    order = api.CollectorOrder
    label = "Collect Framerate"
    hosts = ["nukestudio"]

    def process(self, context):
        for item in context.data.get("selection", []):
            context.data["framerate"] = item.sequence().framerate().toFloat()
            return
