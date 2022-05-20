import os

from maya import cmds

import openpype.api
from openpype.hosts.maya.api.lib import maintained_selection


class ExtractMultiverseLook(openpype.api.Extractor):
    """Extractor for Multiverse USD look data into a Maya Scene."""

    label = "Extract Multiverse USD Look"
    hosts = ["maya"]
    families = ["mvLook"]
    scene_type = "usda"
    file_formats = ["usda", "usd"]

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
            "writeTransforms": False,
            "writeVisibility": False,
            "writeAttributes": False,
            "writeMaterials": True,
            "writeVariants": False,
            "writeVariantsDefinition": False,
            "writeActiveState": False,
            "writeNamespaces": False,
            "numTimeSamples": 1,
            "timeSamplesSpan": 0.0
        }

    def get_file_format(self, instance):
        fileFormat = instance.data["fileFormat"]
        if fileFormat in range(len(self.file_formats)):
            self.scene_type = self.file_formats[fileFormat]

    def process(self, instance):
        # Load plugin first
        cmds.loadPlugin("MultiverseForMaya", quiet=True)

        # Define output file path
        staging_dir = self.staging_dir(instance)
        self.get_file_format(instance)
        file_name = "{0}.{1}".format(instance.name, self.scene_type)
        file_path = os.path.join(staging_dir, file_name)
        file_path = file_path.replace('\\', '/')

        # Parse export options
        options = self.default_options
        self.log.info("Export options: {0}".format(options))

        # Perform extraction
        self.log.info("Performing extraction ...")

        with maintained_selection():
            members = instance.data("setMembers")
            members = cmds.ls(members,
                              dag=True,
                              shapes=False,
                              type="mvUsdCompoundShape",
                              noIntermediate=True,
                              long=True)
            self.log.info('Collected object {}'.format(members))
            if len(members) > 1:
                self.log.error('More than one member: {}'.format(members))

            import multiverse

            over_write_opts = multiverse.OverridesWriteOptions()
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
                # @TODO: Make sure there is only one here.

                self.log.debug("Writing Override for '{}'".format(member))
                multiverse.WriteOverrides(file_path, member, over_write_opts)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': self.scene_type,
            'ext': self.scene_type,
            'files': file_name,
            'stagingDir': staging_dir
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance {} to {}".format(
            instance.name, file_path))
