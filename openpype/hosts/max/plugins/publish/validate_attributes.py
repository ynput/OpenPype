# -*- coding: utf-8 -*-
"""Validator for Attributes."""
from pyblish.api import ContextPlugin, ValidatorOrder
from pymxs import runtime as rt

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    RepairContextAction
)


def has_property(object_name, property_name):
    """Return whether an object has a property with given name"""
    return rt.Execute(f'isProperty {object_name} "{property_name}"')


def is_matching_value(object_name, property_name, value):
    """Return whether an existing property matches value `value"""
    property_value = rt.Execute(f"{object_name}.{property_name}")

    # Wrap property value if value is a string valued attributes
    # starting with a `#`
    if (
        isinstance(value, str) and
        value.startswith("#") and
        not value.endswith(")")
    ):
        # prefix value with `#`
        # not applicable for #() array value type
        # and only applicable for enum i.e. #bob, #sally
        property_value = f"#{property_value}"

    return property_value == value


class ValidateAttributes(OptionalPyblishPluginMixin,
                         ContextPlugin):
    """Validates attributes in the project setting are consistent
    with the nodes from MaxWrapper Class in 3ds max.
    E.g. "renderers.current.separateAovFiles",
         "renderers.production.PrimaryGIEngine"
    Admin(s) need to put the dict below and enable this validator for a check:
    {
       "renderers.current":{
            "separateAovFiles" : True
        },
        "renderers.production":{
            "PrimaryGIEngine": "#RS_GIENGINE_BRUTE_FORCE"
        }
        ....
    }

    """

    order = ValidatorOrder
    hosts = ["max"]
    label = "Attributes"
    actions = [RepairContextAction]
    optional = True

    @classmethod
    def get_invalid(cls, context):
        attributes = (
            context.data["project_settings"]["max"]["publish"]
                        ["ValidateAttributes"]["attributes"]
        )
        if not attributes:
            return
        invalid = []
        for object_name, required_properties in attributes.items():
            if not rt.Execute(f"isValidValue {object_name}"):
                # Skip checking if the node does not
                # exist in MaxWrapper Class
                cls.log.debug(f"Unable to find '{object_name}'."
                              " Skipping validation of attributes.")
                continue

            for property_name, value in required_properties.items():
                if not has_property(object_name, property_name):
                    cls.log.error(
                        "Non-existing property: "
                        f"{object_name}.{property_name}")
                    invalid.append((object_name, property_name))

                if not is_matching_value(object_name, property_name, value):
                    cls.log.error(
                        f"Invalid value for: {object_name}.{property_name}"
                        f" should be: {value}")
                    invalid.append((object_name, property_name))

        return invalid

    def process(self, context):
        if not self.is_active(context.data):
            self.log.debug("Skipping Validate Attributes...")
            return
        invalid_attributes = self.get_invalid(context)
        if invalid_attributes:
            bullet_point_invalid_statement = "\n".join(
                "- {}".format(invalid) for invalid
                in invalid_attributes
            )
            report = (
                "Required Attribute(s) have invalid value(s).\n\n"
                f"{bullet_point_invalid_statement}\n\n"
                "You can use repair action to fix them if they are not\n"
                "unknown property value(s)."
            )
            raise PublishValidationError(
                report, title="Invalid Value(s) for Required Attribute(s)")

    @classmethod
    def repair(cls, context):
        attributes = (
            context.data["project_settings"]["max"]["publish"]
                        ["ValidateAttributes"]["attributes"]
        )
        invalid_attributes = cls.get_invalid(context)
        for attrs in invalid_attributes:
            prop, attr = attrs
            value = attributes[prop][attr]
            if isinstance(value, str) and not value.startswith("#"):
                attribute_fix = '{}.{}="{}"'.format(
                    prop, attr, value
                )
            else:
                attribute_fix = "{}.{}={}".format(
                    prop, attr, value
                )
            rt.Execute(attribute_fix)
