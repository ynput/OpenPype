# -*- coding: utf-8 -*-
"""Cleanup leftover files from publish."""
import os
import shutil
import pyblish.api


class CleanUpJobRoot(pyblish.api.ContextPlugin):
    """Cleans up the job root directory after a successful publish.

    Remove all files in job root as all of them should be published.
    """

    order = pyblish.api.IntegratorOrder + 1
    label = "Clean Up Job Root"
    optional = True
    active = True

    def process(self, context):
        context_staging_dir = context.data.get("contextStagingDir")
        if not context_staging_dir:
            self.log.info("Key 'contextStagingDir' is empty.")

        elif not os.path.exists(context_staging_dir):
            self.log.info((
                "Job root directory for this publish does not"
                " exists anymore \"{}\"."
            ).format(context_staging_dir))
        else:
            self.log.info("Deleting job root with all files.")
            shutil.rmtree(context_staging_dir)
