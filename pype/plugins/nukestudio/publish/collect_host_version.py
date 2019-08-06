import pyblish.api


class CollectHostVersion(pyblish.api.ContextPlugin):
    """Inject the hosts version into context"""

    order = pyblish.api.CollectorOrder

    def process(self, context):
        import nuke

        context.set_data('hostVersion', value=nuke.NUKE_VERSION_STRING)
