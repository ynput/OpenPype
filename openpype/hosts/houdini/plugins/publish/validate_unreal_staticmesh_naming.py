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
    collision_prefixes = []
    static_mesh_prefix = ""

    @classmethod
    def apply_settings(cls, project_settings, system_settings):

        settings = (
            project_settings["houdini"]["create"]["CreateStaticMesh"]
        )
        cls.collision_prefixes = settings["collision_prefixes"]
        cls.static_mesh_prefix = settings["static_mesh_prefix"]

    def process(self, instance):

        if not self.is_active(instance.data):
            return

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

        rop_node = hou.node(instance.data["instance_node"])
        output_node = instance.data.get("output_node")
        if output_node is None:
            cls.log.debug(
                "No Output Node, skipping check.."
            )
            return

        if rop_node.evalParm("buildfrompath"):
            # This validator doesn't support naming check if
            # building hierarchy from path' is used
            cls.log.info(
                "Using 'Build Hierarchy from Path Attribute', skipping check.."
            )
            return

        # Check nodes names
        all_outputs = get_output_children(output_node, include_sops=False)
        for output in all_outputs:
            for prefix in cls.collision_prefixes:
                if output.name().startswith(prefix):
                    invalid.append(output)
                    cls.log.error(
                        "Invalid node name: Node '%s' "
                        "includes a collision prefix '%s'",
                        output.path(), prefix
                    )
                    break

        return invalid
