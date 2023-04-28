import os
import re

import clique
import pyblish.api


class ValidateSequenceFrames(pyblish.api.InstancePlugin):
    """Ensure the sequence of frames is complete

    The files found in the folder are checked against the startFrame and
    endFrame of the instance. If the first or last file is not
    corresponding with the first or last frame it is flagged as invalid.

    Used regular expression pattern handles numbers in the file names
    (eg "Main_beauty.v001.1001.exr", "Main_beauty_v001.1001.exr",
    "Main_beauty.1001.1001.exr") but not numbers behind frames (eg.
    "Main_beauty.1001.v001.exr")
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Sequence Frames"
    families = ["imagesequence", "render"]
    hosts = ["shell", "unreal"]

    def process(self, instance):
        representations = instance.data.get("representations")
        if not representations:
            return
        for repr in representations:
            repr_files = repr["files"]
            if isinstance(repr_files, str):
                continue

            ext = repr.get("ext")
            if not ext:
                _, ext = os.path.splitext(repr_files[0])
            elif not ext.startswith("."):
                ext = ".{}".format(ext)
            pattern = r"\D?(?P<index>(?P<padding>0*)\d+){}$".format(
                re.escape(ext))
            patterns = [pattern]

            collections, remainder = clique.assemble(
                repr_files, minimum_items=1, patterns=patterns)

            assert not remainder, "Must not have remainder"
            assert len(collections) == 1, "Must detect single collection"
            collection = collections[0]
            frames = list(collection.indexes)

            if instance.data.get("slate"):
                # Slate is not part of the frame range
                frames = frames[1:]

            current_range = (frames[0], frames[-1])

            required_range = (instance.data["frameStart"],
                              instance.data["frameEnd"])

            if current_range != required_range:
                raise ValueError(f"Invalid frame range: {current_range} - "
                                 f"expected: {required_range}")

            missing = collection.holes().indexes
            assert not missing, "Missing frames: %s" % (missing,)
