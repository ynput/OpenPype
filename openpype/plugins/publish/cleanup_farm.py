# -*- coding: utf-8 -*-
"""Cleanup leftover files from publish."""
import os
import shutil
import pyblish.api
import avalon.api


class CleanUpFarm(pyblish.api.ContextPlugin):
    """Cleans up the staging directory after a successful publish.

    This will also clean published renders and delete their parent directories.
    """

    order = pyblish.api.IntegratorOrder + 11
    label = "Clean Up Farm"
    enabled = True

    # Keep "filesequence" for backwards compatibility of older jobs
    targets = ["filesequence", "farm"]

    def process(self, context):
        """Plugin entry point."""
        if avalon.api.Session["AVALON_APP"] != "maya":
            self.log.info("Not in farm publish of maya renders. Skipping")
            return

        dirpaths_to_remove = set()
        for instance in context:
            staging_dir = instance.data.get("stagingDir")
            if staging_dir:
                dirpaths_to_remove.add(os.path.normpath(staging_dir))

        # clean dirs which are empty
        for dirpath in dirpaths_to_remove:
            if not os.path.exists(dirpath):
                continue

            try:
                shutil.rmtree(dirpath)
            except OSError:
                self.log.warning(
                    "Failed to remove directory \"{}\"".format(dirpath),
                    exc_info=True
                )
