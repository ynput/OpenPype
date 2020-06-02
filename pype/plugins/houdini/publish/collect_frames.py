import os
import re

import pyblish.api
from pype.hosts.houdini import lib


class CollectFrames(pyblish.api.InstancePlugin):
    """Collect all frames which would be a resukl"""

    order = pyblish.api.CollectorOrder
    label = "Collect Frames"
    families = ["vdbcache"]

    def process(self, instance):

        ropnode = instance[0]

        output_parm = lib.get_output_parameter(ropnode)
        output = output_parm.eval()

        file_name = os.path.basename(output)
        match = re.match("(\w+)\.(\d+)\.vdb", file_name)
        result = file_name

        start_frame = instance.data.get("frameStart", None)
        end_frame = instance.data.get("frameEnd", None)

        if match and start_frame is not None:

            # Check if frames are bigger than 1 (file collection)
            # override the result
            if end_frame - start_frame > 1:
                result = self.create_file_list(match,
                                               int(start_frame),
                                               int(end_frame))

        instance.data.update({"frames": result})

    def create_file_list(self, match, start_frame, end_frame):
        """Collect files based on frame range and regex.match

        Args:
            match(re.match): match object
            start_frame(int): start of the animation
            end_frame(int): end of the animation

        Returns:
            list

        """

        result = []

        padding = len(match.group(2))
        name = match.group(1)
        padding_format = "{number:0{width}d}"

        count = start_frame
        while count <= end_frame:
            str_count = padding_format.format(number=count, width=padding)
            file_name = "{}.{}.vdb".format(name, str_count)
            result.append(file_name)
            count += 1

        return result
