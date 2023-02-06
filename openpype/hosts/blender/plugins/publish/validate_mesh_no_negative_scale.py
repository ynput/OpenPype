from typing import List

import bpy

import pyblish.api

from openpype.pipeline.publish import ValidateContentsOrder
import openpype.hosts.blender.api.action


class ValidateMeshNoNegativeScale(pyblish.api.Validator):
    """Ensure that meshes don't have a negative scale."""

    order = ValidateContentsOrder
    hosts = ["blender"]
    families = ["model"]
    label = "Mesh No Negative Scale"
    actions = [openpype.hosts.blender.api.action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance) -> List:
        invalid = []
        for obj in instance:
            if isinstance(obj, bpy.types.Object) and obj.type == 'MESH':
                if any(v < 0 for v in obj.scale):
                    invalid.append(obj)
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                f"Meshes found in instance with negative scale: {invalid}"
            )
