import clique

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
        representations = instance.data.get("representations")
        for repr in representations:
            patterns = [clique.PATTERNS["frames"]]
            collections, remainder = clique.assemble(
                repr["files"], minimum_items=1, patterns=patterns)

            assert not remainder, "Must not have remainder"
            assert len(collections) == 1, "Must detect single collection"
            collection = collections[0]
            frames = list(collection.indexes)

            current_range = (frames[0], frames[-1])
            required_range = (instance.data["frameStart"],
                              instance.data["frameEnd"])

            if current_range != required_range:
                raise ValueError(f"Invalid frame range: {current_range} - "
                                 f"expected: {required_range}")

            missing = collection.holes().indexes
            assert not missing, "Missing frames: %s" % (missing,)
