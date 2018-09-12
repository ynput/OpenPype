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

        start_frame = float(instance.data["startFrame"])
        end_frame = float(instance.data["endFrame"])

        ropnode = instance[0]
        attributes = {"filename": tmp_filepath,
                      "trange": 2}

        with lib.attribute_values(ropnode, attributes):
            ropnode.render(frame_range=(start_frame, end_frame, 1))

        if "files" not in instance.data:
            instance.data["files"] = []

        instance.data["files"].append(file_name)
