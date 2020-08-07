import pyblish.api


class ValidateSequenceFrames(pyblish.api.InstancePlugin):
    """Ensure the sequence of frames is complete

    The files found in the folder are checked against the startFrame and
    endFrame of the instance. If the first or last file is not
    corresponding with the first or last frame it is flagged as invalid.
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Sequence Frames"
    families = ["imagesequence"]
    hosts = ["shell"]

    def process(self, instance):

        collection = instance[0]
        self.log.info(collection)

        frames = list(collection.indexes)

        current_range = (frames[0], frames[-1])
        required_range = (instance.data["frameStart"],
                          instance.data["frameEnd"])

        if current_range != required_range:
            raise ValueError("Invalid frame range: {0} - "
                             "expected: {1}".format(current_range,
                                                    required_range))

        missing = collection.holes().indexes
        assert not missing, "Missing frames: %s" % (missing,)
