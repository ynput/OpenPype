import os

import avalon.maya
import openpype.api

from maya import cmds


class ExtractMultiverseUsdComposition(openpype.api.Extractor):
    """Extractor of Multiverse USD Composition."""

    label = "Extract Multiverse USD Composition"
    hosts = ["maya"]
    families = ["usdComposition"]

    @property
    def options(self):
        """Overridable options for Multiverse USD Export

        Given in the following format
            - {NAME: EXPECTED TYPE}

        If the overridden option's type does not match,
        the option is not included and a warning is logged.

        """

        return {
            "stripNamespaces": bool,
            "mergeTransformAndShape": bool,
            "flattenContent": bool,
            "writePendingOverrides": bool,
            "writeTimeRange": bool,
            "timeRangeStart": int,
            "timeRangeEnd": int,
            "timeRangeIncrement": int,
            "timeRangeNumTimeSamples": int,
            "timeRangeSamplesSpan": float,
            "timeRangeFramesPerSecond": float
        }

    @property
    def default_options(self):
        """The default options for Multiverse USD extraction."""
        start_frame = int(cmds.playbackOptions(query=True,
                                               animationStartTime=True))
        end_frame = int(cmds.playbackOptions(query=True,
                                             animationEndTime=True))

        return {
            "stripNamespaces": False,
            "mergeTransformAndShape": False,
            "flattenContent": False,
            "writePendingOverrides": False,
            "writeTimeRange": True,
            "timeRangeStart": start_frame,
            "timeRangeEnd": end_frame,
            "timeRangeIncrement": 1,
            "timeRangeNumTimeSamples": 0,
            "timeRangeSamplesSpan": 0.0,
            "timeRangeFramesPerSecond": 24.0
        }

    def process(self, instance):
        # Load plugin firstly
        cmds.loadPlugin("MultiverseForMaya", quiet=True)

        # Define output file path
        staging_dir = self.staging_dir(instance)
        file_name = "{}.usda".format(instance.name)
        file_path = os.path.join(staging_dir, file_name)
        file_path = file_path.replace('\\', '/')

        # Parse export options
        options = self.default_options
        self.log.info("Export options: {0}".format(options))

        # Perform extraction
        self.log.info("Performing extraction ...")

        with avalon.maya.maintained_selection():
            members = instance.data("setMembers")
            members = cmds.ls(members,
                              dag=True,
                              shapes=True,
                              type=("mvUsdCompoundShape"),
                              noIntermediate=True,
                              long=True)
            self.log.info('Collected object {}'.format(members))

            # TODO: Deal with asset, composition, overide with options.
            import multiverse

            time_opts = None
            if options["writeTimeRange"]:
                time_opts = multiverse.TimeOptions()

                time_opts.writeTimeRange = True

                time_range_start = options["timeRangeStart"]
                time_range_end = options["timeRangeEnd"]
                time_opts.frameRange = (time_range_start, time_range_end)

                time_opts.frameIncrement = options["timeRangeIncrement"]
                time_opts.numTimeSamples = options["timeRangeNumTimeSamples"]
                time_opts.timeSamplesSpan = options["timeRangeSamplesSpan"]
                time_opts.framePerSecond = options["timeRangeFramesPerSecond"]

            comp_write_opts = multiverse.CompositionWriteOptions()
            options_items = getattr(options, "iteritems", options.items)
            for (k, v) in options_items:
                if k == "writeTimeRange" or k.startswith("timeRange"):
                    continue
                setattr(comp_write_opts, k, v)
            comp_write_opts.timeOptions = time_opts
            multiverse.WriteComposition(file_path, members, comp_write_opts)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'usda',
            'ext': 'usda',
            'files': file_name,
            "stagingDir": staging_dir
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance {} to {}".format(
            instance.name, file_path))
