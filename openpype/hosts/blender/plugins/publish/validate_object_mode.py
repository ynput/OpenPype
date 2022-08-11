from typing import List

import bpy

import pyblish.api
from openpype.hosts.blender.api.action import SelectInvalidAction


class ValidateObjectIsInObjectMode(pyblish.api.InstancePlugin):
    """Validate that the objects in the instance are in Object Mode."""

    order = pyblish.api.ValidatorOrder - 0.01
    hosts = ["blender"]
    families = ["model", "rig", "layout"]
    category = "geometry"
    label = "Validate Object Mode"
    actions = [SelectInvalidAction]
    optional = False

    @staticmethod
    def get_invalid(cls, instance) -> List:
        invalid = []
        for obj in set(instance):
            if isinstance(obj, bpy.types.Object):
                if not obj.mode == 'OBJECT':
                    invalid.append(obj)
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                f"Object found in instance is not in Object Mode: {invalid}")
