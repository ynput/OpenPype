from typing import List

import bpy
import string

import pyblish.api

import openpype.hosts.blender.api.action
from openpype.pipeline.publish import ValidateContentsOrder


class ValidateSetdressObjectNames(pyblish.api.Validator):
    """Validate that the objects names don't have special characters."""

    order = ValidateContentsOrder
    hosts = ["blender"]
    families = ["setdress"]
    label = "Validate SetDress Objects Name"
    actions = [openpype.hosts.blender.api.action.SelectInvalidAction]
    optional = False

    @staticmethod
    def get_invalid(instance) -> List:
        invalid = []

        # Set of special characters except "_" and "." which is used in naming
        invalid_chars = set(string.punctuation.replace("_",""))
        invalid_chars.remove(".")
        for obj in instance:
            # any is faster than regex to get char in obj.name and return bool
            if obj is not None and any(char in invalid_chars for char in obj.name):
                invalid.append(obj)
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                f"Objects found with special characters in their name: {invalid}"
            )
