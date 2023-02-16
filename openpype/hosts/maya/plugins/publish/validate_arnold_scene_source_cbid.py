import maya.cmds as cmds

import pyblish.api
from openpype.pipeline.publish import (
    ValidateContentsOrder, PublishValidationError, RepairAction
)


class ValidateArnoldSceneSourceCbid(pyblish.api.InstancePlugin):
    """Validate Arnold Scene Source Cbid.

    It is required for the proxy and content nodes to share the same cbid.
    """

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["ass"]
    label = "Validate Arnold Scene Source CBID"
    actions = [RepairAction]

    @staticmethod
    def _get_nodes_data(nodes):
        nodes_by_name = {}
        for node in nodes:
            node_split = node.split("|")
            nodes_by_name[node_split[-1].split(":")[-1]] = node
            for shape in cmds.listRelatives(node, shapes=True):
                basename = shape.split("|")[-1].split(":")[-1]
                nodes_by_name[basename] = node + "|" + shape

        return nodes_by_name

    def get_invalid_couples(self, instance):
        content_nodes_by_name = self._get_nodes_data(
            instance.data["setMembers"]
        )
        proxy_nodes_by_name = self._get_nodes_data(
            instance.data.get("proxy", [])
        )

        invalid_couples = []
        for content_name, content_node in content_nodes_by_name.items():
            for proxy_name, proxy_node in proxy_nodes_by_name.items():
                if content_name == proxy_name:
                    content_value = cmds.getAttr(content_node + ".cbId")
                    proxy_value = cmds.getAttr(proxy_node + ".cbId")
                    if content_value != proxy_value:
                        invalid_couples.append((content_node, proxy_node))

        return invalid_couples

    def process(self, instance):
        # Proxy validation.
        if not instance.data.get("proxy", []):
            return

        # Validate for proxy nodes sharing the same cbId as content nodes.
        invalid_couples = self.get_invalid_couples(instance)
        if invalid_couples:
            raise PublishValidationError(
                "Found proxy nodes with mismatching cbid:\n{}".format(
                    invalid_couples
                )
            )

    @classmethod
    def repair(cls, instance):
        for content_node, proxy_node in cls.get_invalid_couples(cls, instance):
            cmds.setAttr(
                proxy_node + ".cbId",
                cmds.getAttr(content_node + ".cbId"),
                type="string"
            )
