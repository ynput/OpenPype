import pyblish.api


class CollectCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Collect Current File"
    hosts = ["nuke"]

    def process(self, context):
        import os
        import nuke
        current_file = nuke.root().name()

        normalised = os.path.normpath(current_file)

        context.data["current_file"] = normalised
        context.data["currentFile"] = normalised
