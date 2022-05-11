import os

import openpype.api
from openpype.hosts.maya.api.lib import maintained_selection

from maya import cmds


class ExtractMultiverseUsdOverride(openpype.api.Extractor):
    """Extractor for USD Override by Multiverse."""

    label = "Extract Multiverse USD Override"
    hosts = ["maya"]
    families = ["usdOverride"]

    @property
    def options(self):
        """Overridable options for Multiverse USD Export

        Given in the following format
            - {NAME: EXPECTED TYPE}

        If the overridden option's type does not match,
        the option is not included and a warning is logged.

        """

        return {
            "writeAll": bool,
            "writeTransforms": bool,
            "writeVisibility": bool,
            "writeAttributes": bool,
            "writeMaterials": bool,
            "writeVariants": bool,
            "writeVariantsDefinition": bool,
            "writeActiveState": bool,
            "writeNamespaces": bool,
            "numTimeSamples": int,
            "timeSamplesSpan": float
        }

    @property
    def default_options(self):
        """The default options for Multiverse USD extraction."""

        return {
            "writeAll": False,
            "writeTransforms": True,
            "writeVisibility": True,
            "writeAttributes": True,
            "writeMaterials": True,
            "writeVariants": True,
            "writeVariantsDefinition": True,
            "writeActiveState": True,
            "writeNamespaces": False,
            "numTimeSamples": 1,
            "timeSamplesSpan": 0.0
        }

    def process(self, instance):
        # Load plugin firstly
        cmds.loadPlugin("MultiverseForMaya", quiet=True)

        # Define output file path
        staging_dir = self.staging_dir(instance)
        file_name = "{}.usda".format(instance.name)
        file_path = os.path.join(staging_dir, file_name)
        file_path = file_path.replace("\\", "/")

        # Parse export options
        options = self.default_options
        self.log.info("Export options: {0}".format(options))

        # Perform extraction
        self.log.info("Performing extraction ...")

        with maintained_selection():
            members = instance.data("setMembers")
            members = cmds.ls(members,
                              dag=True,
                              shapes=True,
                              type="mvUsdCompoundShape",
                              noIntermediate=True,
                              long=True)
            self.log.info("Collected object {}".format(members))

            # TODO: Deal with asset, composition, overide with options.
            import multiverse

            time_opts = None
            frame_start = instance.data["frameStart"]
            frame_end = instance.data["frameEnd"]
            handle_start = instance.data["handleStart"]
            handle_end = instance.data["handleEnd"]
            step = instance.data["step"]
            fps = instance.data["fps"]
            if frame_end != frame_start:
                time_opts = multiverse.TimeOptions()

                time_opts.writeTimeRange = True
                time_opts.frameRange = (
                    frame_start - handle_start, frame_end + handle_end)
                time_opts.frameIncrement = step
                time_opts.numTimeSamples = instance.data["numTimeSamples"]
                time_opts.timeSamplesSpan = instance.data["timeSamplesSpan"]
                time_opts.framePerSecond = fps

            over_write_opts = multiverse.OverridesWriteOptions(time_opts)
            options_discard_keys = {
                "numTimeSamples",
                "timeSamplesSpan",
                "frameStart",
                "frameEnd",
                "handleStart",
                "handleEnd",
                "step",
                "fps"
            }
            for key, value in options.items():
                if key in options_discard_keys:
                    continue
                setattr(over_write_opts, key, value)

            for member in members:
                multiverse.WriteOverrides(file_path, member, over_write_opts)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "usd",
            "ext": "usd",
            "files": file_name,
            "stagingDir": staging_dir
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance {} to {}".format(
            instance.name, file_path))
