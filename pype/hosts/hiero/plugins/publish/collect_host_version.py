import pyblish.api


class CollectHostVersion(pyblish.api.ContextPlugin):
    """Inject the hosts version into context"""

    label = "Collect Host and HostVersion"
    order = pyblish.api.CollectorOrder - 0.5

    def process(self, context):
        import nuke
        import pyblish.api

        context.set_data("host", pyblish.api.current_host())
        context.set_data('hostVersion', value=nuke.NUKE_VERSION_STRING)
