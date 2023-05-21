import json
import os

from maya import cmds

import pyblish.api

from openpype.pipeline.publish import (
    ValidateContentsOrder, PublishValidationError
)
from openpype.settings.lib import convert_to_int_or_float


class ValidateLightRequired(pyblish.api.InstancePlugin):
    """Validate Light required settings."""

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["light"]
    label = "Validate Light Required"
    light_types = []
    attribute_values = []

    def process(self, instance):
        # Collect validation data.
        invalid_nodes = []
        attribute_nodes = instance.data["setMembers"].copy()
        file_nodes = []
        for node in instance.data["setMembers"]:
            shapes = cmds.listRelatives(node, fullPath=True, shapes=True)
            attribute_nodes.extend(shapes)

            for shape in shapes:
                file_nodes.extend(
                    cmds.listConnections(
                        shape,
                        skipConversionNodes=True,
                        type="file",
                        destination=False
                    )
                )

            shape_types = {x: cmds.nodeType(x) for x in shapes}
            invalid_types = set(shape_types.values()) - set(self.light_types)
            invalid_nodes.extend(
                [x for x in shape_types if shape_types[x] in invalid_types]
            )

        # Validate attributes.
        invalid_attributes = []
        for node in attribute_nodes:
            for node_type_attr, value in self.attribute_values:
                node_type, attr = node_type_attr.split(".")

                if cmds.nodeType(node) != node_type:
                    continue

                if not cmds.attributeQuery(attr, node=node, exists=True):
                    continue

                value = convert_to_int_or_float(value)
                node_attr = "{}.{}".format(node, attr)
                current_value = cmds.getAttr(node_attr)
                if current_value != value:
                    invalid_attributes.append(
                        {
                            "attribute": node_attr,
                            "current_value": current_value,
                            "expected_value": value
                        }
                    )

        if invalid_attributes:
            raise PublishValidationError(
                "Found invalid attributes:\n{}".format(
                    json.dumps(invalid_attributes, indent=4, sort_keys=True)
                )
            )

        # Validations below are not needed when the plugin is optional.
        if self.optional:
            return

        # Validate light types.
        if invalid_nodes:
            raise PublishValidationError(
                "Found invalid light nodes:\n{}".format(invalid_nodes)
            )

        # Validate file textures.
        invalid_file_nodes = []
        for node in file_nodes:
            file_path = cmds.getAttr(node + ".fileTextureName")
            if not os.path.exists(file_path):
                invalid_file_nodes.append(
                    {"path": file_path, "node": node}
                )

        if invalid_file_nodes:
            raise PublishValidationError(
                "Found invalid file nodes with missing file:\n{}".format(
                    json.dumps(invalid_file_nodes, indent=4, sort_keys=True)
                )
            )


class ValidateLightOptional(ValidateLightRequired):
    """Validate Light optional settings."""

    optional = True
    label = "Validate Light Optional"
