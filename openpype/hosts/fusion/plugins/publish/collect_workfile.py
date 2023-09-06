import os

import pyblish.api


class CollectFusionWorkfile(pyblish.api.InstancePlugin):
    """Collect Fusion workfile representation."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Workfile"
    hosts = ["fusion"]
    families = ["workfile"]

    def process(self, instance):

        current_file = instance.context.data["currentFile"]

        folder, file = os.path.split(current_file)
        filename, ext = os.path.splitext(file)

        instance.data['representations'] = [{
            'name': ext.lstrip("."),
            'ext': ext.lstrip("."),
            'files': file,
            "stagingDir": folder,
        }]
