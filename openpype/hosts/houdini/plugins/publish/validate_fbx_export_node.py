# -*- coding: utf-8 -*-
"""Validator plugin for Export node in filmbox instance."""
import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateNoExportPath(pyblish.api.InstancePlugin):
    """Validate if Export node in filmboxfbx instance exists."""

    order = pyblish.api.ValidatorOrder
    families = ["filmboxfbx"]
    label = "Validate Filmbox Export Node"

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Export node is incorrect",
                title="Invalid Export Node"
            )

    @classmethod
    def get_invalid(cls, instance):

        import hou

        fbx_rop = hou.node(instance.data.get("instance_node"))
        export_node = fbx_rop.parm("startnode").evalAsNode()

        if not export_node:
            cls.log.error(
                ("Empty Export ('Export' parameter) found in "
                 "the filmbox instance - {}".format(fbx_rop.path()))
            )
            return [fbx_rop]

        if not isinstance(export_node, hou.SopNode):
            cls.log.error(
                "Export node '{}' is not pointing to valid SOP"
                " node".format(export_node.path())
            )
            return [export_node]
