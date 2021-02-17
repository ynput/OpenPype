import pyblish.api
from avalon import api


class CollectTime(pyblish.api.ContextPlugin):
    """Store global time at the time of publish"""

    label = "Collect Current Time"
    order = pyblish.api.CollectorOrder

    def process(self, context):
        context.data["time"] = api.time()
