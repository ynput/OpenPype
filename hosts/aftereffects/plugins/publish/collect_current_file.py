import os

import pyblish.api

from openpype.hosts.aftereffects.api import get_stub


class CollectCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.49
    label = "Current File"
    hosts = ["aftereffects"]

    def process(self, context):
        context.data["currentFile"] = os.path.normpath(
            get_stub().get_active_document_full_name()
        ).replace("\\", "/")
