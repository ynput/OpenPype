import pyblish.api
from openpype.lib import get_formatted_current_time


class CollectTime(pyblish.api.ContextPlugin):
    """Store global time at the time of publish"""

    label = "Collect Current Time"
    order = pyblish.api.CollectorOrder - 0.499

    def process(self, context):
        context.data["time"] = get_formatted_current_time()
