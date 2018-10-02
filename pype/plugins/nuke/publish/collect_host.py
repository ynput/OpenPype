import pyblish.api


class CollectHost(pyblish.api.ContextPlugin):
    """Inject the host into context"""

    order = pyblish.api.CollectorOrder
    label = "Collect Host"
    hosts = ["nuke"]

    def process(self, context):
        import pyblish.api

        context.data["host"] = pyblish.api.current_host()
