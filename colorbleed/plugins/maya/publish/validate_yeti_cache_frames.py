import os

import pyblish.api
import colorbleed.api


class ValidateYetiCacheFrames(pyblish.api.InstancePlugin):
    """Validates Yeti nodes have existing cache frames"""

    order = colorbleed.api.ValidateContentsOrder
    label = 'Yeti Cache Frames'
    families = ['colorbleed.furYeti']
    actions = [colorbleed.api.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):

        # Check if all frames cache exists for given node.
        start_frame = instance.data.get("startFrame")
        end_frame = instance.data.get("endFrame")
        required = range(int(start_frame), int(end_frame) + 1)

        yeti_caches = instance.data.get('yetiCaches', {})
        invalid = []

        for node, data in yeti_caches.items():
            cls.log.info("Validating node: {0}".format(node))

            source = data.get("source", None)
            sequences = data.get("sequences", [])

            if not source:
                invalid.append(node)
                cls.log.warning("Node has no cache file name set: "
                                "{0}".format(node))
                continue

            folder = os.path.dirname(source)
            if not folder or not os.path.exists(folder):
                invalid.append(node)
                cls.log.warning("Cache folder does not exist: "
                                "{0} {1}".format(node, folder))
                continue

            if not sequences:
                invalid.append(node)
                cls.log.warning("Sequence does not exist: "
                                "{0} {1}".format(node, source))
                continue

            if len(sequences) != 1:
                invalid.append(node)
                cls.log.warning("More than one sequence found? "
                                "{0} {1}".format(node, source))
                cls.log.warning("Found caches: {0}".format(sequences))
                continue

            sequence = sequences[0]

            start = sequence.start()
            end = sequence.end()
            if start > start_frame or end < end_frame:
                invalid.append(node)
                cls.log.warning("Sequence does not have enough "
                                "frames: {0}-{1} (requires: {2}-{3})"
                                "".format(start, end,
                                          start_frame,
                                          end_frame))
                continue

            # Ensure all frames are present
            missing = set(sequence.missing())
            required_missing = [x for x in required if x in missing]
            if required_missing:

                invalid.append(node)
                cls.log.warning("Sequence is missing required frames: "
                                "{0}".format(required_missing))
                continue

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error("Invalid nodes: {0}".format(invalid))
            raise RuntimeError("Invalid yeti nodes in instance. "
                               "See logs for details.")
