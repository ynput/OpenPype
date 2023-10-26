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

        invalid_attributes = [key for key, value in attributes.items()
                              if rt.Execute(attributes[key]) != value]

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
        invalid_attribute_keys = cls.get_invalid(context)
        for key in invalid_attribute_keys:
            attributes[key] = rt.Execute(attributes[key])
