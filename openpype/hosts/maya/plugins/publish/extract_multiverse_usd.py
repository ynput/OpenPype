import os

import avalon.maya
import openpype.api

from maya import cmds


class ExtractMultiverseUsd(openpype.api.Extractor):
    """Extractor for USD by Multiverse."""

    label = "Extract Multiverse USD"
    hosts = ["maya"]
    families = ["usd"]

    def process(self, instance):
        # Load plugin firstly
        cmds.loadPlugin("MultiverseForMaya", quiet=True)

        # Define output file path
        staging_dir = self.staging_dir(instance)
        file_name = "{}.usd".format(instance.name)
        file_path = os.path.join(staging_dir, file_name)
        file_path = file_path.replace('\\', '/')

        # Perform extraction
        self.log.info("Performing extraction ...")

        with avalon.maya.maintained_selection():
            members = instance.data("setMembers")
            members = cmds.ls(members,
                              dag=True,
                              shapes=True,
                              type=("mesh"),
                              noIntermediate=True,
                              long=True)

            # TODO: Deal with asset, composition, overide with options.
            import multiverse
            options = multiverse.AssetWriteOptions()
            multiverse.WriteAsset(file_path, members, options)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'usd',
            'ext': 'usd',
            'files': file_name,
            "stagingDir": staging_dir
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted {} to {}".format(instance, file_path))
