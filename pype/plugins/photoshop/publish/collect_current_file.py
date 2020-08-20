import os

import pyblish.api

from pype.modules.websocket_server.clients.photoshop_client import (
    PhotoshopClientStub
)


class CollectCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Current File"
    hosts = ["photoshop"]

    def process(self, context):
        photoshop_client = PhotoshopClientStub()
        context.data["currentFile"] = os.path.normpath(
            photoshop_client.get_active_document_full_name()
        ).replace("\\", "/")
