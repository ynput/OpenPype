import os

import pyblish.api
import colorbleed.api
from colorbleed.houdini import lib


class ExtractAlembic(colorbleed.api.Extractor):

    order = pyblish.api.ExtractorOrder
    label = "Extract Pointcache (Alembic)"
    hosts = ["houdini"]
    families = ["colorbleed.pointcache"]

    def process(self, instance):

        staging_dir = self.staging_dir(instance)

        file_name = "{}.abc".format(instance.data["subset"])
        tmp_filepath = os.path.join(staging_dir, file_name)

        ropnode = instance[0]

        # Set file name to staging dir + file name
        attributes = {"filename": tmp_filepath}

        # We run the render with the input settings set by the user
        with lib.attribute_values(ropnode, attributes):
            ropnode.render()

        if "files" not in instance.data:
            instance.data["files"] = []

        instance.data["files"].append(file_name)
