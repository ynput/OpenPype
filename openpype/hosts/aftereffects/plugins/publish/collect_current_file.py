import os

import pyblish.api

from avalon import aftereffects


class CollectCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.49
    label = "Current File"
    hosts = ["aftereffects"]

    def process(self, context):
        context.data["currentFile"] = os.path.normpath(
            aftereffects.stub().get_active_document_full_name()
        ).replace("\\", "/")
