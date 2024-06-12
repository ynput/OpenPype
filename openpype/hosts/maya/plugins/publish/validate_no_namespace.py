import maya.cmds as cmds

import pyblish.api
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)

import openpype.hosts.maya.api.action


def _as_report_list(values, prefix="- ", suffix="\n"):
    """Return list as bullet point list for a report"""
    if not values:
        return ""
    return prefix + (suffix + prefix).join(values)


def get_namespace(node_name):
    # ensure only node's name (not parent path)
    node_name = node_name.rsplit("|", 1)[-1]
    # ensure only namespace
    return node_name.rpartition(":")[0]


class ValidateNoNamespace(pyblish.api.InstancePlugin,
                          OptionalPyblishPluginMixin):
    """Ensure the nodes don't have a namespace"""

    order = ValidateContentsOrder
    hosts = ['maya']
    families = ['model']
    label = 'No Namespaces'
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction,
               RepairAction]
    optional = False

    @staticmethod
    def get_invalid(instance):
        nodes = cmds.ls(instance, long=True)
        return [node for node in nodes if get_namespace(node)]

    def process(self, instance):
        """Process all the nodes in the instance"""
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError(
                "Namespaces found:\n\n{0}".format(
                    _as_report_list(sorted(invalid))
                ),
                title="Namespaces in model"
            )

    @classmethod
    def repair(cls, instance):
        """Remove all namespaces from the nodes in the instance"""

        invalid = cls.get_invalid(instance)

        # Iterate over the nodes by long to short names to iterate the lowest
        # in hierarchy nodes first. This way we avoid having renamed parents
        # before renaming children nodes
        for node in sorted(invalid, key=len, reverse=True):

            node_name = node.rsplit("|", 1)[-1]
            node_name_without_namespace = node_name.rsplit(":")[-1]
            cmds.rename(node, node_name_without_namespace)
