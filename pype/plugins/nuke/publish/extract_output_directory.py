import os

import pyblish.api


class ExtractOutputDirectory(pyblish.api.InstancePlugin):
    """Extracts the output path for any collection or single output_path."""

    order = pyblish.api.ExtractorOrder - 0.05
    label = "Output Directory"
    optional = True

    # targets = ["process"]

    def process(self, instance):

        path = None

        if "output_path" in instance.data.keys():
            path = instance.data["path"]

        if not path:
            return

        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
