# -*- coding: utf-8 -*-
"""Validator for correct naming of Static Meshes."""
import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from openpype.pipeline.publish import ValidateContentsOrder

from openpype.hosts.houdini.api.action import SelectInvalidAction

import hou


class ValidateMeshIsStatic(pyblish.api.InstancePlugin,
                                   OptionalPyblishPluginMixin):
    """Validate mesh is static.

    It checks if output node is time dependant.
    """

    families = ["staticMesh"]
    hosts = ["houdini"]
    label = "Validate Mesh is Static"
    order = ValidateContentsOrder + 0.1
    actions = [SelectInvalidAction]

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            nodes = [n.path() for n in invalid if isinstance(n, hou.Node)]
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



        if output_node.name().isTimeDependent():
            invalid.append(output_node)
            cls.log.error(
                "Output node '%s' is time dependent.",
                output_node.name()
            )

        if output_node.childTypeCategory() == hou.objNodeTypeCategory():
            for child in output_node.children():
                    if output_node.name().isTimeDependent():
                        invalid.append(child)
                        cls.log.error(
                            "Child node '%s' in '%s' "
                            "his time dependent.",
                            child.name(), output_node.path()
                        )
                        break

        return invalid
