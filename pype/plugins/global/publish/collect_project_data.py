"""
Requires:
    None

Provides:
    context     -> projectData
"""

import pyblish.api
import pype.api as pype


class CollectProjectData(pyblish.api.ContextPlugin):
    """Collecting project data from avalon db"""

    label = "Collect Project Data"
    order = pyblish.api.CollectorOrder - 0.1
    hosts = ["nukestudio"]

    def process(self, context):
        # get project data from avalon db
        context.data["projectData"] = pype.get_project()["data"]

        return
