import os
import re

import hou
import pyblish.api
from openpype.hosts.houdini.api import lib


def splitext(name, allowed_multidot_extensions):

    for ext in allowed_multidot_extensions:
        if name.endswith(ext):
            return name[:-len(ext)], ext

    return os.path.splitext(name)


class CollectFrames(pyblish.api.InstancePlugin):
    """Collect all frames which would be saved from the ROP nodes"""

    order = pyblish.api.CollectorOrder
    label = "Collect Frames"
    families = ["vdbcache", "imagesequence", "ass"]

    def process(self, instance):

        ropnode = instance[0]

        start_frame = instance.data.get("frameStart", None)
        end_frame = instance.data.get("frameEnd", None)

        output_parm = lib.get_output_parameter(ropnode)
        if start_frame is not None:
            # When rendering only a single frame still explicitly
            # get the name for that particular frame instead of current frame
            output = output_parm.evalAtFrame(start_frame)
        else:
            self.log.warning("Using current frame: {}".format(hou.frame()))
            output = output_parm.eval()

        _, ext = splitext(output,
                          allowed_multidot_extensions=[".ass.gz"])
        file_name = os.path.basename(output)
        result = file_name

        # Get the filename pattern match from the output
        # path so we can compute all frames that would
        # come out from rendering the ROP node if there
        # is a frame pattern in the name
        pattern = r"\w+\.(\d+)" + re.escape(ext)
        match = re.match(pattern, file_name)

        if match and start_frame is not None:

            # Check if frames are bigger than 1 (file collection)
            # override the result
            if end_frame - start_frame > 0:
                result = self.create_file_list(
                    match, int(start_frame), int(end_frame)
                )

        # todo: `frames` currently conflicts with "explicit frames" for a
        #       for a custom frame list. So this should be refactored.
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

        # Get the padding length
        frame = match.group(1)
        padding = len(frame)

        # Get the parts of the filename surrounding the frame number
        # so we can put our own frame numbers in.
        span = match.span(1)
        prefix = match.string[: span[0]]
        suffix = match.string[span[1]:]

        # Generate filenames for all frames
        result = []
        for i in range(start_frame, end_frame + 1):

            # Format frame number by the padding amount
            str_frame = "{number:0{width}d}".format(number=i, width=padding)

            file_name = prefix + str_frame + suffix
            result.append(file_name)

        return result
