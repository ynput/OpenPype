import os

import pyblish.api
import pype.api


class ValidateEditorialResources(pyblish.api.InstancePlugin):
    """Validate there is a "mov" next to the editorial file."""

    label = "Validate Editorial Resources"
    hosts = ["standalonepublisher"]
    families = ["audio", "review"]
    order = pype.api.ValidateContentsOrder

    def process(self, instance):
        check_file = instance.data["editorialVideoPath"]
        msg = f"Missing \"{check_file}\"."
        assert check_file, msg
