import os
import shutil
import pyblish.api


class CleanUp(pyblish.api.InstancePlugin):
    """Cleans up the staging directory after a successful publish.

    The removal will only happen for staging directories which are inside the
    temporary folder, otherwise the folder is ignored.

    """

    order = pyblish.api.IntegratorOrder + 10
    label = "Clean Up"
    exclude_families = ["clip"]
    optional = True
    active = False

    def process(self, instance):
        if [ef for ef in self.exclude_families
                if instance.data["family"] in ef]:
            return
        import tempfile

        staging_dir = instance.data.get("stagingDir", None)
        if not staging_dir or not os.path.exists(staging_dir):
            self.log.info("No staging directory found: %s" % staging_dir)
            return

        temp_root = tempfile.gettempdir()
        if not os.path.normpath(staging_dir).startswith(temp_root):
            self.log.info("Skipping cleanup. Staging directory is not in the "
                          "temp folder: %s" % staging_dir)
            return

        self.log.info("Removing temporary folder ...")
        shutil.rmtree(staging_dir)
