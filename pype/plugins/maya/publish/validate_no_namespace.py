import pymel.core as pm
import maya.cmds as cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action


def get_namespace(node_name):
    # ensure only node's name (not parent path)
    node_name = node_name.rsplit("|")[-1]
    # ensure only namespace
    return node_name.rpartition(":")[0]


class ValidateNoNamespace(pyblish.api.InstancePlugin):
    """Ensure the nodes don't have a namespace"""

    order = pype.api.ValidateContentsOrder
    hosts = ['maya']
    families = ['model']
    category = 'cleanup'
    version = (0, 1, 0)
    label = 'No Namespaces'
    actions = [pype.hosts.maya.action.SelectInvalidAction,
               pype.api.RepairAction]

    @staticmethod
    def get_invalid(instance):
        nodes = cmds.ls(instance, long=True)
        return [node for node in nodes if get_namespace(node)]

    def process(self, instance):
        """Process all the nodes in the instance"""
        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Namespaces found: {0}".format(invalid))

    @classmethod
    def repair(cls, instance):
        """Remove all namespaces from the nodes in the instance"""

        invalid = cls.get_invalid(instance)

        # Get nodes with pymel since we'll be renaming them
        # Since we don't want to keep checking the hierarchy
        # or full paths
        nodes = pm.ls(invalid)

        for node in nodes:
            namespace = node.namespace()
            if namespace:
                name = node.nodeName()
                node.rename(name[len(namespace):])
