# -*- coding: utf-8 -*-
"""Cleanup leftover files from publish."""
import os
import shutil
import pyblish.api

from openpype.pipeline import legacy_io


class CleanUpFarm(pyblish.api.ContextPlugin):
    """Cleans up the staging directory after a successful publish.

    This will also clean published renders and delete their parent directories.
    """

    order = pyblish.api.IntegratorOrder + 11
    label = "Clean Up Farm"
    enabled = True

    # Keep "filesequence" for backwards compatibility of older jobs
    targets = ["filesequence", "farm"]
    allowed_hosts = ("maya", )

    def process(self, context):
        # Get source host from which farm publishing was started
        src_host_name = legacy_io.Session.get("AVALON_APP")
        self.log.debug("Host name from session is {}".format(src_host_name))
        # Skip process if is not in list of source hosts in which this
        #    plugin should run
        if src_host_name not in self.allowed_hosts:
            self.log.info((
                "Source host \"{}\" is not in list of enabled hosts {}."
                " Skipping"
            ).format(str(src_host_name), str(self.allowed_hosts)))
            return

        self.log.debug("Preparing filepaths to remove")
        # Collect directories to remove
        dirpaths_to_remove = set()
        for instance in context:
            staging_dir = instance.data.get("stagingDir")
            if staging_dir:
                dirpaths_to_remove.add(os.path.normpath(staging_dir))

            if "representations" in instance.data:
                for repre in instance.data["representations"]:
                    staging_dir = repre.get("stagingDir")
                    if staging_dir:
                        dirpaths_to_remove.add(os.path.normpath(staging_dir))

        if not dirpaths_to_remove:
            self.log.info("Nothing to remove. Skipping")
            return

        self.log.debug("Filepaths to remove are:\n{}".format(
            "\n".join(["- {}".format(path) for path in dirpaths_to_remove])
        ))

        # clean dirs which are empty
        for dirpath in dirpaths_to_remove:
            if not os.path.exists(dirpath):
                self.log.debug("Skipping not existing directory \"{}\"".format(
                    dirpath
                ))
                continue

            self.log.debug("Removing directory \"{}\"".format(dirpath))
            try:
                shutil.rmtree(dirpath)
            except OSError:
                self.log.warning(
                    "Failed to remove directory \"{}\"".format(dirpath),
                    exc_info=True
                )
