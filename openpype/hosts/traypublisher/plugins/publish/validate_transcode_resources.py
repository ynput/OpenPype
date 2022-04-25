import pyblish.api
import openpype.api


class ValidateTranscodeResources(pyblish.api.InstancePlugin):
    """Validate there is a "wav" next to the editorial file."""

    label = "Validate Delivery Resources"
    hosts = ["traypublisher"]
    families = ["transcode"]
    order = openpype.api.ValidateContentsOrder
    optional = True

    def process(self, instance):
        check_file = instance.data["audioPath"]
        msg = f"No audio file found. Audio path: \"{check_file}\"."
        assert check_file, msg