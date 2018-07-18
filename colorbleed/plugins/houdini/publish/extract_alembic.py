import os

import hou

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
        attributes = {"trange": 1,
                      "f1": instance.data["startFrame"],
                      "f2": instance.data["endFrame"]}

        with lib.attribute_values(ropnode, attributes):
            ropnode.execute()

        if "files" not in instance.data:
            instance.data["files"] = []

        instance.data["files"].append(tmp_filepath)
