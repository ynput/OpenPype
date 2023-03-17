import os

from maya import cmds

from openpype.pipeline import publish
from openpype.hosts.maya.api.lib import (
    maintained_selection, attribute_values, delete_after
)


class ExtractGPUCache(publish.Extractor):
    """Extract the content of the instance to an CPU cache file."""

    label = "CPU Cache"
    hosts = ["maya"]
    families = ["model"]

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        filename = "{}.abc".format(instance.name)

        # Write out GPU cache file.
        cmds.gpuCache(
            instance[:],
            directory=staging_dir,
            fileName=filename,
            saveMultipleFiles=False
        )

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "gpu_cache",
            "ext": "abc",
            "files": filename,
            "stagingDir": staging_dir,
            "data": {"heroSuffix": "gpu_cache"}
        }

        instance.data["representations"].append(representation)

        self.log.info(
            "Extracted instance {} to: {}".format(instance.name, staging_dir)
        )
