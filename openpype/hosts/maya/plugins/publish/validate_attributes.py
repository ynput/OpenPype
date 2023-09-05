from collections import defaultdict

import pyblish.api
from maya import cmds

from openpype.hosts.maya.api.lib import set_attribute
from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    RepairAction,
    ValidateContentsOrder,
)


class ValidateAttributes(pyblish.api.InstancePlugin,
                         OptionalPyblishPluginMixin):
    """Ensure attributes are consistent.

    Attributes to validate and their values comes from the
    "maya/attributes.json" preset, which needs this structure:
        {
          "family": {
            "node_name.attribute_name": attribute_value
          }
        }
    """

    order = ValidateContentsOrder
    label = "Attributes"
    hosts = ["maya"]
    actions = [RepairAction]
    optional = True

    attributes = None

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        # Check for preset existence.
        if not self.attributes:
            return

        invalid = self.get_invalid(instance, compute=True)
        if invalid:
            raise PublishValidationError(
                "Found attributes with invalid values: {}".format(invalid)
            )

    @classmethod
    def get_invalid(cls, instance, compute=False):
        if compute:
            return cls.get_invalid_attributes(instance)
        else:
            return instance.data.get("invalid_attributes", [])

    @classmethod
    def get_invalid_attributes(cls, instance):
        invalid_attributes = []

        # Filter families.
        families = [instance.data["family"]]
        families += instance.data.get("families", [])
        families = set(families) & set(cls.attributes.keys())
        if not families:
            return []

        # Get all attributes to validate.
        attributes = defaultdict(dict)
        for family in families:
            if family not in cls.attributes:
                # No attributes to validate for family
                continue

            for preset_attr, preset_value in cls.attributes[family].items():
                node_name, attribute_name = preset_attr.split(".", 1)
                attributes[node_name][attribute_name] = preset_value

        if not attributes:
            return []

        # Get invalid attributes.
        nodes = cmds.ls(long=True)
        for node in nodes:
            node_name = node.rsplit("|", 1)[-1].rsplit(":", 1)[-1]
            if node_name not in attributes:
                continue

            for attr_name, expected in attributes[node_name].items():

                # Skip if attribute does not exist
                if not cmds.attributeQuery(attr_name, node=node, exists=True):
                    continue

                plug = "{}.{}".format(node, attr_name)
                value = cmds.getAttr(plug)
                if value != expected:
                    invalid_attributes.append(
                        {
                            "attribute": plug,
                            "expected": expected,
                            "current": value
                        }
                    )

        instance.data["invalid_attributes"] = invalid_attributes
        return invalid_attributes

    @classmethod
    def repair(cls, instance):
        invalid = cls.get_invalid(instance)
        for data in invalid:
            node, attr = data["attribute"].split(".", 1)
            value = data["expected"]
            set_attribute(node=node, attribute=attr, value=value)
