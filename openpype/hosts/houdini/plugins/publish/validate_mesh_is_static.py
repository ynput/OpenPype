# -*- coding: utf-8 -*-
"""Validator for correct naming of Static Meshes."""
import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from openpype.pipeline.publish import ValidateContentsOrder

from openpype.hosts.houdini.api.action import SelectInvalidAction
from openpype.hosts.houdini.api.lib import get_output_children


class ValidateMeshIsStatic(pyblish.api.InstancePlugin,
                           OptionalPyblishPluginMixin):
    """Validate mesh is static.

    It checks if output node is time dependent.
    """

    families = ["staticMesh"]
    hosts = ["houdini"]
    label = "Validate Mesh is Static"
    order = ValidateContentsOrder + 0.1
    actions = [SelectInvalidAction]

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            nodes = [n.path() for n in invalid]
            raise PublishValidationError(
                "See log for details. "
                "Invalid nodes: {0}".format(nodes)
            )

    @classmethod
    def get_invalid(cls, instance):

        invalid = []

        output_node = instance.data.get("output_node")
        if output_node is None:
            cls.log.debug(
                "No Output Node, skipping check.."
            )
            return

        all_outputs = get_output_children(output_node)

        for output in all_outputs:
            if output.isTimeDependent():
                invalid.append(output)
                cls.log.error(
                    "Output node '%s' is time dependent.",
                    output.path()
                )

        return invalid
