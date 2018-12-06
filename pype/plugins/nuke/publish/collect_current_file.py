import pyblish.api


class SelectCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder
    hosts = ["nuke"]

    def process(self, context):
        import os
        import nuke
        current_file = nuke.root().name()

        normalised = os.path.normpath(current_file)

        context.data["current_file"] = normalised
        context.data["currentFile"] = normalised
