import pyblish.api
import pype.action
import maya.cmds as cmds
import pype.hosts.maya.action


class ValidateYetiRigCacheState(pyblish.api.InstancePlugin):
    """Validate the I/O attributes of the node

    Every pgYetiMaya cache node per instance should have:
        1. Input Mode is set to `None`
        2. Input Cache File Name is empty

    """

    order = pyblish.api.ValidatorOrder
    label = "Yeti Rig Cache State"
    hosts = ["maya"]
    families = ["yetiRig"]
    actions = [pype.action.RepairAction,
               pype.hosts.maya.action.SelectInvalidAction]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Nodes have incorrect I/O settings")

    @classmethod
    def get_invalid(cls, instance):

        invalid = []

        yeti_nodes = cmds.ls(instance, type="pgYetiMaya")
        for node in yeti_nodes:
            # Check reading state
            state = cmds.getAttr("%s.fileMode" % node)
            if state == 1:
                cls.log.error("Node `%s` is set to mode `cache`" % node)
                invalid.append(node)
                continue

            # Check reading state
            has_cache = cmds.getAttr("%s.cacheFileName" % node)
            if has_cache:
                cls.log.error("Node `%s` has a cache file set" % node)
                invalid.append(node)
                continue

        return invalid

    @classmethod
    def repair(cls, instance):
        """Repair all errors"""

        # Create set to ensure all nodes only pass once
        invalid = cls.get_invalid(instance)
        for node in invalid:
            cmds.setAttr("%s.fileMode" % node, 0)
            cmds.setAttr("%s.cacheFileName" % node, "", type="string")
