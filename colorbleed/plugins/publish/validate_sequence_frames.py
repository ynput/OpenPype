import pyblish.api


class ValidateSequenceFrames(pyblish.api.InstancePlugin):

    order = pyblish.api.ValidatorOrder
    label = "Validate Sequence Frames"
    families = ["colorbleed.imagesequence", "colorbleed.yeticache"]

    def process(self, instance):

        collection = instance[0]
        frames = collection.indexes

        assert frames[0] == instance.data["startFrame"]
        assert frames[-1] == instance.data["endFrame"]

        missing = collection.holes
        assert not missing, "Missing frames: %s" % (missing,)
