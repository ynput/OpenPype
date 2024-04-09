import os
import re

import pyblish.api

from openpype.pipeline.publish import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)

def is_cache_resource(resource):
    """Return whether resource is a cacheFile resource"""
    required = set(["maya", "node", "cacheFile"])
    tags = resource.get("tags", [])
    return required.issubset(tags)


def valdidate_files(files):
    for f in files:
        assert os.path.exists(f)
        assert f.endswith(".mcx") or f.endswith(".mcc")

    return True


def filter_ticks(files):
    tick_files = set()
    ticks = set()
    for path in files:
        match = re.match(".+Tick([0-9]+).mcx$", os.path.basename(path))
        if match:
            tick_files.add(path)
            num = match.group(1)
            ticks.add(int(num))

    return tick_files, ticks


class ValidateInstancerFrameRanges(pyblish.api.InstancePlugin,
                                   OptionalPyblishPluginMixin):
    """Validates all instancer particle systems are cached correctly.

    This means they should have the files/frames as required by the start-end
    frame (including handles).

    This also checks the files exist and checks the "ticks" (substeps) files.

    """
    order = pyblish.api.ValidatorOrder
    label = 'Instancer Cache Frame Ranges'
    families = ['instancer']
    optional = False

    @classmethod
    def get_invalid(cls, instance):

        import pyseq

        start_frame = instance.data.get("frameStart", 0)
        end_frame = instance.data.get("frameEnd", 0)
        required = range(int(start_frame), int(end_frame) + 1)

        invalid = list()
        resources = instance.data.get("resources", [])

        for resource in resources:
            if not is_cache_resource(resource):
                continue

            node = resource['node']
            all_files = resource['files'][:]
            all_lookup = set(all_files)

            # The first file is usually the .xml description file.
            xml = all_files.pop(0)
            assert xml.endswith(".xml")

            # Ensure all files exist (including ticks)
            # The remainder file paths should be the .mcx or .mcc files
            valdidate_files(all_files)

            # Maya particle caches support substeps by saving out additional
            # files that end with a Tick60.mcx, Tick120.mcx, etc. suffix.
            # To avoid `pyseq` getting confused we filter those out and then
            # for each file (except the last frame) check that at least all
            # ticks exist.

            tick_files, ticks = filter_ticks(all_files)
            if tick_files:
                files = [f for f in all_files if f not in tick_files]
            else:
                files = all_files

            sequences = pyseq.get_sequences(files)
            if len(sequences) != 1:
                invalid.append(node)
                cls.log.warning("More than one sequence found? "
                                "{0} {1}".format(node, files))
                cls.log.warning("Found caches: {0}".format(sequences))
                continue

            sequence = sequences[0]
            cls.log.debug("Found sequence: {0}".format(sequence))

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
            if missing:
                required_missing = [x for x in required if x in missing]
                if required_missing:
                    invalid.append(node)
                    cls.log.warning("Sequence is missing required frames: "
                                    "{0}".format(required_missing))
                    continue

            # Ensure all tick files (substep) exist for the files in the folder
            # for the frames required by the time range.
            if ticks:
                ticks = list(sorted(ticks))
                cls.log.debug("Found ticks: {0} "
                              "(substeps: {1})".format(ticks, len(ticks)))

                # Check all frames except the last since we don't
                # require subframes after our time range.
                tick_check_frames = set(required[:-1])

                # Check all frames
                for item in sequence:
                    frame = item.frame
                    if not frame:
                        invalid.append(node)
                        cls.log.error("Path is not a frame in sequence: "
                                      "{0}".format(item))
                        continue

                    # Not required for our time range
                    if frame not in tick_check_frames:
                        continue

                    path = item.path
                    for num in ticks:
                        base, ext = os.path.splitext(path)
                        tick_file = base + "Tick{0}".format(num) + ext
                        if tick_file not in all_lookup:
                            invalid.append(node)
                            cls.log.warning("Tick file found that is not "
                                            "in cache query filenames: "
                                            "{0}".format(tick_file))

        return invalid

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error("Invalid nodes: {0}".format(invalid))
            raise PublishValidationError(
                ("Invalid particle caches in instance. "
                 "See logs for details."))
