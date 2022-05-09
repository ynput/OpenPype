import os

from maya import cmds

import openpype.api
from openpype.hosts.maya.api.lib import maintained_selection


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
            "numTimeSamples": int,
            "timeSamplesSpan": float
        }

    @property
    def default_options(self):
        """The default options for Multiverse USD extraction."""

        return {
            "stripNamespaces": True,
            "mergeTransformAndShape": False,
            "flattenContent": False,
            "writePendingOverrides": False,
            "numTimeSamples": 1,
            "timeSamplesSpan": 0.0
        }

    def parse_overrides(self, instance, options):
        """Inspect data of instance to determine overridden options"""

        for key in instance.data:
            if key not in self.options:
                continue

            # Ensure the data is of correct type
            value = instance.data[key]
            if not isinstance(value, self.options[key]):
                self.log.warning(
                    "Overridden attribute {key} was of "
                    "the wrong type: {invalid_type} "
                    "- should have been {valid_type}".format(
                        key=key,
                        invalid_type=type(value).__name__,
                        valid_type=self.options[key].__name__))
                continue

            options[key] = value

        return options

    def process(self, instance):
        # Load plugin firstly
        cmds.loadPlugin("MultiverseForMaya", quiet=True)

        # Define output file path
        staging_dir = self.staging_dir(instance)
        file_name = "{}.usd".format(instance.name)
        file_path = os.path.join(staging_dir, file_name)
        file_path = file_path.replace('\\', '/')

        # Parse export options
        options = self.default_options
        options = self.parse_overrides(instance, options)
        self.log.info("Export options: {0}".format(options))

        # Perform extraction
        self.log.info("Performing extraction ...")

        with maintained_selection():
            members = instance.data("setMembers")
            self.log.info('Collected object {}'.format(members))

            import multiverse

            time_opts = None
            frame_start = instance.data['frameStart']
            frame_end = instance.data['frameEnd']
            handle_start = instance.data['handleStart']
            handle_end = instance.data['handleEnd']
            step = instance.data['step']
            fps = instance.data['fps']
            if frame_end != frame_start:
                time_opts = multiverse.TimeOptions()

                time_opts.writeTimeRange = True
                time_opts.frameRange = (
                    frame_start - handle_start, frame_end + handle_end)
                time_opts.frameIncrement = step
                time_opts.numTimeSamples = instance.data["numTimeSamples"]
                time_opts.timeSamplesSpan = instance.data["timeSamplesSpan"]
                time_opts.framePerSecond = fps

            comp_write_opts = multiverse.CompositionWriteOptions()

            """ 
            OP tells MV to write to a staging directory, and then moves the
            file to it's final publish directory. By default, MV write relative
            paths, but these paths will break when the referencing file moves.
            This option forces writes to absolute paths, which is ok within OP
            because all published assets have static paths, and MV can only 
            reference published assets. When a proper UsdAssetResolver is used,
            this won't be needed.
            """
            comp_write_opts.forceAbsolutePaths = True

            options_discard_keys = {
                'numTimeSamples',
                'timeSamplesSpan',
                'frameStart',
                'frameEnd',
                'handleStart',
                'handleEnd',
                'step',
                'fps'
            }
            for key, value in options.items():
                if key in options_discard_keys:
                    continue
                setattr(comp_write_opts, key, value)

            multiverse.WriteComposition(file_path, members, comp_write_opts)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'usd',
            'ext': 'usd',
            'files': file_name,
            "stagingDir": staging_dir
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance {} to {}".format(
            instance.name, file_path))
