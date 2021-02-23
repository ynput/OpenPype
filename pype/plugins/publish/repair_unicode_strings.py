import os
import pyblish.api
import pype.api


class RepairUnicodeStrings(pyblish.api.Collector):
    """Validate all environment variables are string type.

    """

    order = pyblish.api.CollectorOrder
    label = 'Unicode Strings'

    def process(self, instance):
        # invalid = self.get_invalid(instance)
        # if invalid:
        for key, value in os.environ.items():
            self.log.info(type(value))
            if type(value) is type(u't'):
                os.environ[key] = str(value)

    @classmethod
    def get_invalid(cls, instance):
        invalid = []
        for key, value in os.environ.items():
            if type(value) is type(u't'):
                invalid.append((key, value))

        return invalid
