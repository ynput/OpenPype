from maya import cmds

import pyblish.api

from avalon import maya

import openpype.api
import openpype.hosts.maya.api.action


class ValidateRigCycleError(pyblish.api.InstancePlugin):
    """Validate rig nodes produce have no cycle errors."""

    order = openpype.api.ValidateContentsOrder + 0.05
    label = "Rig Cycle Errors"
    hosts = ["maya"]
    families = ["rig"]
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    optional = True

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Rig nodes produce a cycle error: %s" % invalid)

    @classmethod
    def get_invalid(cls, instance):

        with maya.maintained_selection():
            cmds.select(instance[:], noExpand=True)
            plugs = cmds.cycleCheck(all=False,  # check selection only
                                    list=True)
            invalid = cmds.ls(plugs, objectsOnly=True, long=True)
            return invalid
