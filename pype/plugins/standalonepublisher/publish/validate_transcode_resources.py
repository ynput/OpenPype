import pyblish.api
import pype.api


class ValidateTranscodeResources(pyblish.api.InstancePlugin):
    """Validate there is a "wav" next to the editorial file."""

    label = "Validate Delivery Resources"
    hosts = ["standalonepublisher"]
    families = ["transcode"]
    order = pype.api.ValidateContentsOrder
    optional = True

    def process(self, instance):
        check_file = instance.data["audioPath"]
        msg = f"No audio file found. Audio path: \"{check_file}\"."
        assert check_file, msg
