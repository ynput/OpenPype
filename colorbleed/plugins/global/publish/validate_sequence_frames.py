import pyblish.api


class ValidateSequenceFrames(pyblish.api.InstancePlugin):
    """Ensure the sequence of frames is complete

    The files found in the folder are checked against the startFrame and
    endFrame of the instance. If the first or last file is not
    corresponding with the first or last frame it is flagged as invalid.
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Sequence Frames"
    families = ["colorbleed.imagesequence", "colorbleed.yeticache"]
    hosts = ["shell"]

    def process(self, instance):

        collection = instance[0]

        self.log.warning(collection)
        frames = list(collection.indexes)

        assert frames[0] == instance.data["startFrame"]
        assert frames[-1] == instance.data["endFrame"]

        missing = collection.holes().indexes
        assert not missing, "Missing frames: %s" % (missing,)
