import os

import pyblish.api

from avalon import photoshop


class CollectCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Current File"
    hosts = ["photoshop"]

    def process(self, context):
        context.data["currentFile"] = os.path.normpath(
            photoshop.stub().get_active_document_full_name()
        ).replace("\\", "/")
