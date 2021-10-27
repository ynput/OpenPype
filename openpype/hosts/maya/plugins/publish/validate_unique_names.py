from maya import cmds

import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action


class ValidateUniqueNames(pyblish.api.Validator):
    """shape and shape's vertex can't have any values

    To solve this issue, try freezing the shapes. So long
    as the translation, rotation and scaling values are zero,
    you're all good.

    """

    order = openpype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Unique transform name"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):
        """Returns the invalid transforms in the instance.

        Returns:
            list: Non unique transform name

        """

        return [tr for tr in cmds.ls(instance, type="transform")
                if '|' in tr]

    def process(self, instance):
        """Process all the nodes in the instance "objectSet"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Nodes found with none unique names. "
                             "values: {0}".format(invalid))
