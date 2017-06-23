import pyblish.api


class CollectMindbenderComment(pyblish.api.ContextPlugin):
    """This plug-ins displays the comment dialog box per default"""

    label = "Collect Mindbender Time"
    order = pyblish.api.CollectorOrder

    def process(self, context):
        context.data["comment"] = ""
