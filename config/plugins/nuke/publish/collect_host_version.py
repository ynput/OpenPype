import pyblish.api


class CollectHostVersion(pyblish.api.ContextPlugin):
    """Inject the hosts version into context"""

    order = pyblish.api.CollectorOrder
    label = "Collect Host Version"
    hosts = ["nuke"]

    def process(self, context):
        import nuke
        context.data["hostVersion"] = nuke.NUKE_VERSION_STRING
