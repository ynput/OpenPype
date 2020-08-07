import os
from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


class ValidateUnicodeStrings(pyblish.api.Validator):
    """Validate all environment variables are string type.

    """

    order = pype.api.ValidateContentsOrder
    hosts = ['maya']
    families = ['review']
    label = 'Unicode Strings'
    actions = [pype.api.RepairAction]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found unicode strings in environment variables.")

    @classmethod
    def get_invalid(cls, instance):
        invalid = []
        for key, value in os.environ.items():
            if type(value) is type(u't'):
                invalid.append((key, value))

        return invalid

    @classmethod
    def repair(cls, instance):
        """Retype all unicodes to strings."""

        for key, value in os.environ.items():
            if type(value) is type(u't'):
                os.environ[key] = str(value)
