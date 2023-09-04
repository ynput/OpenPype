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


class ValidateUnrealStaticMeshName(pyblish.api.InstancePlugin,
                                   OptionalPyblishPluginMixin):
    """Validate name of Unreal Static Mesh.

    This validator checks if output node name has a collision prefix:
            - UBX
            - UCP
            - USP
            - UCX

    This validator also checks if subset name is correct
            - {static mesh prefix}_{Asset-Name}{Variant}.

    """

    families = ["staticMesh"]
    hosts = ["houdini"]
    label = "Unreal Static Mesh Name (FBX)"
    order = ValidateContentsOrder + 0.1
    actions = [SelectInvalidAction]

    optional = True

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        settings = (
            project_settings["houdini"]["create"]["CreateUnrealStaticMesh"]
        )
        cls.collision_prefixes = settings["collision_prefixes"]
        cls.static_mesh_prefix = settings["static_mesh_prefix"]

    def process(self, instance):

        if not self.is_active(instance.data):
            return

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

        rop_node = hou.node(instance.data["instance_node"])
        output_node = instance.data.get("output_node")
        if output_node is None:
            cls.log.debug(
                "No Output Node, skipping check.."
            )
            return

        # Check nodes names
        if output_node.childTypeCategory() == hou.objNodeTypeCategory():
            for child in output_node.children():
                for prefix in cls.collision_prefixes:
                    if child.name().startswith(prefix):
                        invalid.append(child)
                        cls.log.error(
                            "Invalid name: Child node '%s' in '%s' "
                            "has a collision prefix '%s'",
                            child.name(), output_node.path(), prefix
                        )
                        break
        else:
            cls.log.debug(output_node.name())
            for prefix in cls.collision_prefixes:
                if output_node.name().startswith(prefix):
                    invalid.append(output_node)
                    cls.log.error(
                        "Invalid name: output node '%s' "
                        "has a collision prefix '%s'",
                        output_node.name(), prefix
                    )

        # Check subset name
        subset_name = "{}_{}{}".format(
            cls.static_mesh_prefix,
            instance.data["asset"],
            instance.data.get("variant", "")
        )

        if instance.data.get("subset") != subset_name:
            invalid.append(rop_node)
            cls.log.error(
                "Invalid subset name on rop node '%s' should be '%s'.",
                rop_node.path(), subset_name
            )

        return invalid

    def get_outputs(self, output_node):

        if output_node.childTypeCategory() == hou.objNodeTypeCategory():
            out_list = [output_node]
            for child in output_node.children():
                out_list += self.get_outputs(child)

            return out_list

        elif output_node.childTypeCategory() == hou.sopNodeTypeCategory():
            return [output_node, self.get_obj_output(output_node)]

    def get_obj_output(self, obj_node):
        """Find sop output node,   """

        outputs = obj_node.subnetOutputs()

        if not outputs:
            return

        elif len(outputs) == 1:
            return outputs[0]

        else:
            return min(outputs,
                       key=lambda node: node.evalParm('outputidx'))
