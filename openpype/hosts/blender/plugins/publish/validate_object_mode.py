from typing import List

import bpy

import pyblish.api
import openpype.hosts.blender.api.action


class ValidateObjectIsInObjectMode(pyblish.api.InstancePlugin):
    """Validate that the objects in the instance are in Object Mode."""

    order = pyblish.api.ValidatorOrder - 0.01
    hosts = ["blender"]
    families = ["model", "rig", "layout", "setdress"]
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
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                f"Object found in instance is not in Object Mode: {invalid}"
            )
