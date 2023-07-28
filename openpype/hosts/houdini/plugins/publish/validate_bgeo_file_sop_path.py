# -*- coding: utf-8 -*-
"""Validator plugin for SOP Path in bgeo isntance."""
import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateNoSOPPath(pyblish.api.InstancePlugin):
    """Validate if SOP Path in BGEO instance exists."""

    order = pyblish.api.ValidatorOrder
    families = ["bgeo"]
    label = "Validate BGEO SOP Path"

    def process(self, instance):

        import hou

        node = hou.node(instance.data.get("instance_node"))
        sop_path = node.evalParm("soppath")
        if not sop_path:
            raise PublishValidationError(
                ("Empty SOP Path ('soppath' parameter) found in "
                 f"the BGEO instance Geometry - {node.path()}"))
        if not isinstance(hou.node(sop_path), hou.SopNode):
            raise PublishValidationError(
                "SOP path is not pointing to valid SOP node.")
