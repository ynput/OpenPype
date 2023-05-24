"""Collect Anatomy object.

Requires:
    context -> projectName

Provides:
    context -> anatomy (openpype.pipeline.anatomy.Anatomy)
"""

import pyblish.api
from openpype.pipeline import Anatomy, KnownPublishError


class CollectAnatomyObject(pyblish.api.ContextPlugin):
    """Collect Anatomy object into Context.

    Order offset could be changed to '-0.45'.
    """

    order = pyblish.api.CollectorOrder - 0.4
    label = "Collect Anatomy Object"

    def process(self, context):
        project_name = context.data.get("projectName")
        if project_name is None:
            raise KnownPublishError((
                "Project name is not set in 'projectName'."
                "Could not initialize project's Anatomy."
            ))

        context.data["anatomy"] = Anatomy(project_name)

        self.log.debug(
            "Anatomy object collected for project \"{}\".".format(project_name)
        )
