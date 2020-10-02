import pyblish.api
import pype.api


class ValidateEditorialResources(pyblish.api.InstancePlugin):
    """Validate there is a "mov" next to the editorial file."""

    label = "Validate Editorial Resources"
    hosts = ["standalonepublisher"]
    families = ["clip"]

    order = pype.api.ValidateContentsOrder

    def process(self, instance):
        self.log.debug(
            f"Instance: {instance}, Families: "
            f"{[instance.data['family']] + instance.data['families']}")
        check_file = instance.data["editorialVideoPath"]
        msg = f"Missing \"{check_file}\"."
        assert check_file, msg
