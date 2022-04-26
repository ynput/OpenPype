from maya import cmds

import pyblish.api

import openpype.api
import openpype.hosts.maya.api.action
from openpype.hosts.maya.api.lib import maintained_selection


class ValidateCycleError(pyblish.api.InstancePlugin):
    """Validate nodes produce no cycle errors."""

    order = openpype.api.ValidateContentsOrder + 0.05
    label = "Cycle Errors"
    hosts = ["maya"]
    families = ["rig"]
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    optional = True

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Nodes produce a cycle error: %s" % invalid)

    @classmethod
    def get_invalid(cls, instance):

        with maintained_selection():
            cmds.select(instance[:], noExpand=True)
            plugs = cmds.cycleCheck(all=False,  # check selection only
                                    list=True)
            invalid = cmds.ls(plugs, objectsOnly=True, long=True)
            return invalid
