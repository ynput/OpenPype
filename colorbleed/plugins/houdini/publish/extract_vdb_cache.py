import os
import re

import pyblish.api
import colorbleed.api

import hou


class ExtractVDBCache(colorbleed.api.Extractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract VDB Cache"
    families = ["colorbleed.vdbcache"]
    hosts = ["houdini"]

    def process(self, instance):

        ropnode = instance[0]

        # Get the filename from the filename parameter
        # `.evalParm(parameter)` will make sure all tokens are resolved
        output = ropnode.evalParm("sopoutput")
        staging_dir = os.path.normpath(os.path.dirname(output))
        instance.data["stagingDir"] = staging_dir

        # Replace the 4 digits to match file sequence token '%04d' if we have
        # a sequence of frames
        file_name = os.path.basename(output)
        has_frame = re.match("\w\.(d+)\.vdb", file_name)
        if has_frame:
            frame_nr = has_frame.group()
            file_name.replace(frame_nr, "%04d")

        # We run the render
        start_frame = instance.data.get("startFrame", None)
        end_frame = instance.data.get("endFrame", None)
        if all(f for f in [start_frame, end_frame]):
            self.log.info(
                "Starting render: {} - {}".format(start_frame, end_frame)
            )

        # Ensure output folder exists
        if not os.path.isdir(staging_dir):
            os.makedirs(staging_dir)

            assert os.path.exists(staging_dir)

        if instance.data.get("executeBackground", True):
            self.log.info("Creating background task..")
            ropnode.parm("executebackground").pressButton()
            self.log.info("Finished")
        else:
            ropnode.render()

        if "files" not in instance.data:
            instance.data["files"] = []

        instance.data["files"].append(file_name)
