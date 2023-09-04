# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
from openpype.hosts.houdini.api.action import (
    SelectInvalidAction,
    SelectROPAction,
)

import hou


class ValidateOutputNode(pyblish.api.InstancePlugin):
    """Validate the instance Output Node.

    This will ensure:
        - The Output Node Path is set.
        - The Output Node Path refers to an existing object.
    """

    order = pyblish.api.ValidatorOrder
    families = ["fbx"]
    hosts = ["houdini"]
    label = "Validate Output Node"
    actions = [SelectROPAction, SelectInvalidAction]

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Output node(s) are incorrect",
                title="Invalid output node(s)"
            )

    @classmethod
    def get_invalid(cls, instance):
        output_node = instance.data.get("output_node")

        if output_node is None:
            rop_node = hou.node(instance.data["instance_node"])
            cls.log.error(
                "Output node in '%s' does not exist. "
                "Ensure a valid output path is set.", rop_node.path()
            )

            return [rop_node]

        if output_node.type().category().name() not in ["Sop", "Object"]:
            cls.log.error(
                "Output node %s is not a SOP or OBJ node. "
                "It must point to a SOP or OBJ node, "
                "instead found category type: %s"
                % (output_node.path(), output_node.type().category().name())
            )
            return [output_node]
