import os

import pyblish.api
import pype.api


class ValidateEditorialResources(pyblish.api.InstancePlugin):
    """Validate there is a "mov" next to the editorial file."""

    label = "Validate Editorial Resources"
    hosts = ["standalonepublisher"]
    families = ["editorial"]
    order = pype.api.ValidateContentsOrder

    # presets
    check_ext = None

    def process(self, instance):
        check_ext = self.check_ext or "mov"
        representation = instance.data["representations"][0]
        staging_dir = representation["stagingDir"]
        basename = os.path.splitext(
            os.path.basename(representation["files"])
        )[0]

        files = [x for x in os.listdir(staging_dir)]

        # Check for correct extansion in file name.
        filename = basename + check_ext
        filepath = os.path.join(staging_dir, filename)
        msg = f"Missing \"{filepath}\"."
        assert filename in files, msg
