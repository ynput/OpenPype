from pyblish import api

class CollectFramerate(api.ContextPlugin):
    """Collect framerate from selected sequence."""

    order = api.CollectorOrder + 0.01
    label = "Collect Framerate"
    hosts = ["nukestudio"]

    def process(self, context):
        sequence = context.data["activeSequence"]
        context.data["fps"] = sequence.framerate().toFloat()
