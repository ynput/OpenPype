import json
import os

import pyblish.api

import pype.api


class ExtractProjection(pype.api.Extractor):
    """Extract projection."""

    label = "Extract Projection"
    hosts = ["maya"]
    families = ["projection"]
    order = pyblish.api.ExtractorOrder

    def process(self, instance):
        staging_dir = self.staging_dir(instance)

        json_fname = "{0}.json".format(instance.name)
        json_path = os.path.join(staging_dir, json_fname)
        with open(json_path, "w") as f:
            json.dump(instance.data["jsonData"], f, sort_keys=True, indent=4)

        instance.data["representations"] = [
            {
                "name": "json",
                "ext": "json",
                "files": json_fname,
                "stagingDir": staging_dir
            }
        ]
