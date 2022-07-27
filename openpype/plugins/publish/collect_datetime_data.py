"""These data *must* be collected only once during publishing process.

Provides:
    context -> datetimeData
"""

import pyblish.api
from openpype.lib.dateutils import get_datetime_data


class CollectDateTimeData(pyblish.api.ContextPlugin):
    order = pyblish.api.CollectorOrder
    label = "Collect DateTime data"

    def process(self, context):
        key = "datetimeData"
        if key not in context.data:
            context.data[key] = get_datetime_data()
