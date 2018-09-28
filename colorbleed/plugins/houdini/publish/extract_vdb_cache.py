import os
import re

import pyblish.api
import colorbleed.api


class ExtractVDBCache(colorbleed.api.Extractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract VDB Cache"
    families = ["colorbleed.vdbcache"]
    hosts = ["houdini"]

    def process(self, instance):

        ropnode = instance[0]

        # Get the filename from the filename parameter
        # `.eval()` will make sure all tokens are resolved
        output = ropnode.parm("sopoutput").eval()
        staging_dir = os.path.dirname(output)
        instance.data["stagingDir"] = staging_dir

        # Replace the 4 digits to match file sequence token '%04d' if we have
        # a sequence of frames
        file_name = os.path.basename(output)
        has_frame = re.match("\w\.(d+)\.vdb", file_name)
        if has_frame:
            frame_nr = has_frame.group()
            file_name.replace(frame_nr, "%04d")

        # We run the render
        #self.log.info(
        #    "Starting render: {startFrame} - {endFrame}".format(**instance.data)
        #)
        ropnode.render()

        if "files" not in instance.data:
            instance.data["files"] = []

        instance.data["files"].append(file_name)
