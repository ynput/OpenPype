"""Collect Anatomy object.

Requires:
    os.environ -> AVALON_PROJECT

Provides:
    context -> anatomy (pype.api.Anatomy)
"""
import os
from pype.api import Anatomy
import pyblish.api


class CollectAnatomyObject(pyblish.api.ContextPlugin):
    """Collect Anatomy object into Context"""

    order = pyblish.api.CollectorOrder - 0.4
    label = "Collect Anatomy Object"

    def process(self, context):
        project_name = os.environ.get("AVALON_PROJECT")
        if project_name is None:
            raise AssertionError(
                "Environment `AVALON_PROJECT` is not set."
                "Could not initialize project's Anatomy."
            )

        context.data["anatomy"] = Anatomy(project_name)

        self.log.info(
            "Anatomy object collected for project \"{}\".".format(project_name)
        )
