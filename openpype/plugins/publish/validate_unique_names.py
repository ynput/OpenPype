from maya import cmds

import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action


class ValidateUniqueNames(pyblish.api.Validator):
    """transform names should be unique

    ie: using cmds.ls(someNodeName) should always return shortname

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
            list: Non unique name transforms

        """

        return [tr for tr in cmds.ls(instance, type="transform")
                if '|' in tr]

    def process(self, instance):
        """Process all the nodes in the instance "objectSet"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Nodes found with none unique names. "
                             "values: {0}".format(invalid))
