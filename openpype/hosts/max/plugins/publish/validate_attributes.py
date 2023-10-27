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
            invalid_attributes = [key for key, value in property_name.items()
                                  if rt.Execute("{}.{}".format(
                                      wrap_object, property_name[key]))!=value]

            return invalid_attributes

    def process(self, context):
        if not self.is_active(context.data):
            self.log.debug("Skipping Validate Attributes...")
            return
        invalid_attributes = self.get_invalid(context)
        if invalid_attributes:
            bullet_point_invalid_statement = "\n".join(
                "- {}".format(invalid) for invalid in invalid_attributes
            )
            report = (
                "Required Attribute(s) have invalid value(s).\n\n"
                f"{bullet_point_invalid_statement}\n\n"
                "You can use repair action to fix it."
            )
            raise PublishValidationError(
                report, title="Invalid Value(s) for Required Attribute(s)")

    @classmethod
    def repair(cls, context):
        attributes = (
            context.data["project_settings"]["max"]["publish"]
                        ["ValidateAttributes"]["attributes"]
        )
        for wrap_object, property_name in attributes.items():
            invalid_attributes = [key for key, value in property_name.items()
                                  if rt.Execute("{}.{}".format(
                                      wrap_object, property_name[key]))!=value]
            for attrs in invalid_attributes:
                rt.Execute("{}.{}={}".format(
                    wrap_object, attrs, attributes[wrap_object][attrs]))
