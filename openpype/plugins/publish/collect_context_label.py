"""
Optional:
    context     -> hostName (str)
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
        # Add ability to use custom context label
        label = context.data.get("label")
        if label:
            self.log.debug("Context label is already set to \"{}\"".format(
                label
            ))
            return

        host_name = context.data.get("hostName")
        if not host_name:
            host_name = pyblish.api.registered_hosts()[-1]
        # Use host name as base for label
        label = host_name.title()

        # Get scene name from "currentFile" and use basename as ending of label
        path = context.data.get("currentFile")
        if path:
            label += " - {}".format(os.path.basename(path))

        # Set label
        context.data["label"] = label
        self.log.debug("Context label is changed to \"{}\"".format(
            label
        ))
