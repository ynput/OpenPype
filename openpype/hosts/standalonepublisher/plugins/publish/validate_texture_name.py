import pyblish.api
import openpype.api


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
        assert "NOT_AVAIL" not in instance.data["asset_build"], msg

        instance.data.pop("asset_build")

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

        assert not missing_key_values, msg
