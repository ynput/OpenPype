import os
import pype.api as pype
import pyblish.api


class CollectScriptVersion(pyblish. api.ContextPlugin):
    """Collect Script Version."""

    order = pyblish.api.CollectorOrder
    label = "Collect Script Version"
    hosts = [
        "nuke",
        "nukeassist"
    ]

    def process(self, context):
        file_path = context.data["currentFile"]
        base_name = os.path.basename(file_path)
        # get version string
        version = pype.get_version_from_path(base_name)

        context.data['version'] = version
