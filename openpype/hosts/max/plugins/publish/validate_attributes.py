# -*- coding: utf-8 -*-
"""Validator for Attributes."""
from pyblish.api import ContextPlugin, ValidatorOrder
from pymxs import runtime as rt

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    RepairContextAction
)


class ValidateAttributes(OptionalPyblishPluginMixin,
                         ContextPlugin):
    """Validates attributes are consistent in 3ds max."""

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

        for wrap_object, property_name in attributes.items():
            invalid_properties = [key for key in property_name.keys()
                                  if not rt.Execute(
                                      f'isProperty {wrap_object} "{key}"')]
            if invalid_properties:
                cls.log.error(
                    "Unknown Property Values:{}".format(invalid_properties))
                return invalid_properties
            # TODO: support multiple varaible types in maxscript
            invalid_attributes = []
            for key, value in property_name.items():
                property_key = rt.Execute("{}.{}".format(
                    wrap_object, key))
                if isinstance(value, str) and (
                    value.startswith("#") and not value.endswith(")")
                ):
                    # not applicable for #() array value type
                    # and only applicable for enum i.e. #bob, #sally
                    if "#{}".format(property_key) != value:
                        invalid_attributes.append((wrap_object, key))
                else:
                    if property_key != value:
                        invalid_attributes.append((wrap_object, key))

            return invalid_attributes

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
                "unknown property value(s)"
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
