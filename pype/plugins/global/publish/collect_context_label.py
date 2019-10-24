"""
Requires:
    context     -> currentFile (str)
Provides:
    context     -> label (str)
"""

import os
import pyblish.api


class CollectContextLabel(pyblish.api.ContextPlugin):
    """Labelize context using the registered host and current file"""

    order = pyblish.api.CollectorOrder + 0.25
    label = "Context Label"

    def process(self, context):

        # Get last registered host
        host = pyblish.api.registered_hosts()[-1]

        # Get scene name from "currentFile"
        path = context.data.get("currentFile") or "<Unsaved>"
        base = os.path.basename(path)

        # Set label
        label = "{host} - {scene}".format(host=host.title(), scene=base)
        if host == "standalonepublisher":
            label = host.title()
        context.data["label"] = label
