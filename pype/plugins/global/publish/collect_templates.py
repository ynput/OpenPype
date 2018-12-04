
from app.api import (
    Templates
)

import pyblish.api


class CollectTemplates(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder
    label = "Collect Templates"

    def process(self, context):
        """Inject the current working file"""
        templates = Templates(
            type=["anatomy"]
        )
        context.data['anatomy'] = templates.anatomy
