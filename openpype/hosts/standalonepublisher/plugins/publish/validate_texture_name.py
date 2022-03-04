import pyblish.api

import openpype.api
from openpype.pipeline import PublishXmlValidationError

class ValidateTextureBatchNaming(pyblish.api.InstancePlugin):
    """Validates that all instances had properly formatted name."""

    label = "Validate Texture Batch Naming"
    hosts = ["standalonepublisher"]
    order = openpype.api.ValidateContentsOrder
    families = ["texture_batch_workfile", "textures"]
    optional = False

    def process(self, instance):
        file_name = instance.data["representations"][0]["files"]
        if isinstance(file_name, list):
            file_name = file_name[0]

        msg = "Couldn't find asset name in '{}'\n".format(file_name) + \
              "File name doesn't follow configured pattern.\n" + \
              "Please rename the file."

        formatting_data = {"file_name": file_name}
        if "NOT_AVAIL" in instance.data["asset_build"]:
            raise PublishXmlValidationError(self, msg,
                                            formatting_data=formatting_data)

        instance.data.pop("asset_build")  # not needed anymore

        if instance.data["family"] == "textures":
            file_name = instance.data["representations"][0]["files"][0]
            self._check_proper_collected(instance.data["versionData"],
                                         file_name)

    def _check_proper_collected(self, versionData, file_name):
        """
            Loop through collected versionData to check if name parsing was OK.
        Args:
            versionData: (dict)

        Returns:
            raises AssertionException
        """
        missing_key_values = []
        for key, value in versionData.items():
            if not value:
                missing_key_values.append(key)

        msg = "Collected data {} doesn't contain values for {}".format(
            versionData, missing_key_values) + "\n" + \
            "Name of the texture file doesn't match expected pattern.\n" + \
            "Please rename file(s) {}".format(file_name)

        missing_str = ','.join(["'{}'".format(key)
                                for key in missing_key_values])
        formatting_data = {"file_name": file_name,
                           "missing_str": missing_str}
        if missing_key_values:
            raise PublishXmlValidationError(self, msg, key="missing_values",
                                            formatting_data=formatting_data)
