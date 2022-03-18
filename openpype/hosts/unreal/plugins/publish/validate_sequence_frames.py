from pathlib import Path

import unreal

import pyblish.api


class ValidateSequenceFrames(pyblish.api.InstancePlugin):
    """Ensure the sequence of frames is complete

    The files found in the folder are checked against the frameStart and
    frameEnd of the instance. If the first or last file is not
    corresponding with the first or last frame it is flagged as invalid.
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Sequence Frames"
    families = ["render"]
    hosts = ["unreal"]
    optional = True

    def process(self, instance):
        self.log.debug(instance.data)

        representations = instance.data.get("representations")
        for repr in representations:
            frames = []
            for x in repr.get("files"):
                # Get frame number. The last one contains the file extension,
                # while the one before that is the frame number.
                # `lstrip` removes any leading zeros. `or "0"` is to tackle
                # the case where the frame number is "00".
                frame = int(str(x).split('.')[-2])
                frames.append(frame)
            frames.sort()
            current_range = (frames[0], frames[-1])
            required_range = (instance.data["frameStart"],
                              instance.data["frameEnd"])

            if current_range != required_range:
                raise ValueError(f"Invalid frame range: {current_range} - "
                                 f"expected: {required_range}")

            assert len(frames) == int(frames[-1]) - int(frames[0]) + 1, \
                "Missing frames"
