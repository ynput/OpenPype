import os
import json

import maya.app.renderSetup.model.renderSetup as renderSetup
from openpype.pipeline import publish


class ExtractRenderSetup(publish.Extractor):
    """
    Produce renderSetup template file

    This will save whole renderSetup to json file for later use.
    """

    label = "Extract RenderSetup"
    hosts = ["maya"]
    families = ["rendersetup"]

    def process(self, instance):
        parent_dir = self.staging_dir(instance)
        json_filename = "{}.json".format(instance.name)
        json_path = os.path.join(parent_dir, json_filename)

        with open(json_path, "w+") as file:
            json.dump(
                renderSetup.instance().encode(None),
                fp=file, indent=2, sort_keys=True)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'json',
            'ext': 'json',
            'files': json_filename,
            "stagingDir": parent_dir,
        }
        instance.data["representations"].append(representation)

        self.log.debug(
            "Extracted instance '%s' to: %s" % (instance.name, json_path))
