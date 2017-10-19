import os

from pyblish import api


class CleanUp(api.InstancePlugin):
    """Cleans up the staging directory after a successful publish

    """

    order = api.IntegratorOrder + 10
    label = "Clean Up"

    def process(self, instance):
        return

    def clean_up(self, instance):
        staging_dir = instance.get("stagingDir", None)
        if staging_dir and os.path.exists(staging_dir):
            self.log.info("Removing temporary folder ...")
            os.rmdir(staging_dir)
