"""These data *must* be collected only once during publishing process.

Provides:
    context -> datetimeData
"""

import pyblish.api
from pype.api import config


class CollectDateTimeData(pyblish.api.ContextPlugin):
    order = pyblish.api.CollectorOrder
    label = "Collect DateTime data"

    def process(self, context):
        key = "datetimeData"
        if key not in context.data:
            context.data[key] = config.get_datetime_data()
