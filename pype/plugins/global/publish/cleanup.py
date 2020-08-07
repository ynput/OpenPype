import os
import shutil
import pyblish.api


def clean_renders(instance):
    transfers = instance.data.get("transfers", list())

    current_families = instance.data.get("families", list())
    instance_family = instance.data.get("family", None)
    dirnames = []

    for src, dest in transfers:
        if os.path.normpath(src) != os.path.normpath(dest):
            if instance_family == 'render' or 'render' in current_families:
                os.remove(src)
                dirnames.append(os.path.dirname(src))

    # make unique set
    cleanup_dirs = set(dirnames)
    for dir in cleanup_dirs:
        try:
            os.rmdir(dir)
        except OSError:
            # directory is not empty, skipping
            continue


class CleanUp(pyblish.api.InstancePlugin):
    """Cleans up the staging directory after a successful publish.

    This will also clean published renders and delete their parent directories.

    """

    order = pyblish.api.IntegratorOrder + 10
    label = "Clean Up"
    exclude_families = ["clip"]
    optional = True
    active = True

    def process(self, instance):
        # Get the errored instances
        failed = []
        for result in instance.context.data["results"]:
            if (result["error"] is not None and result["instance"] is not None
               and result["instance"] not in failed):
                failed.append(result["instance"])
        assert instance not in failed, (
            "Result of '{}' instance were not success".format(
                instance.data["name"]
            )
        )

        self.log.info("Cleaning renders ...")
        clean_renders(instance)

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

        self.log.info("Removing staging directory ...")
        shutil.rmtree(staging_dir)
