import os
import pyblish.api
import pype.api


class RepairUnicodeStrings(pyblish.api.Collector):
    """Validate all environment variables are string type.

    """

    order = pyblish.api.CollectorOrder
    label = 'Unicode Strings'
    actions = [pype.api.RepairContextAction]

    def process(self, context):
        for key, value in os.environ.items():
            os.environ[str(key)] = str(value)
