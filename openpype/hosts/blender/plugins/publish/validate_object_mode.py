from typing import List

import bpy

import pyblish.api
from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError
)
import openpype.hosts.blender.api.action


class ValidateObjectIsInObjectMode(
        pyblish.api.InstancePlugin,
        OptionalPyblishPluginMixin,
):
    """Validate that the objects in the instance are in Object Mode."""

    order = pyblish.api.ValidatorOrder - 0.01
    hosts = ["blender"]
    families = ["model", "rig", "layout"]
    label = "Validate Object Mode"
    actions = [openpype.hosts.blender.api.action.SelectInvalidAction]
    optional = False

    @staticmethod
    def get_invalid(instance) -> List:
        invalid = []
        for obj in instance:
            if isinstance(obj, bpy.types.Object) and obj.mode != "OBJECT":
                invalid.append(obj)
        return invalid

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            names = ", ".join(obj.name for obj in invalid)
            raise PublishValidationError(
                f"Object found in instance is not in Object Mode: {names}"
            )
