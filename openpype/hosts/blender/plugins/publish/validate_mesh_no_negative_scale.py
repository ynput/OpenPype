from typing import List

import bpy

import pyblish.api
import openpype.api
import openpype.hosts.blender.api.action


class ValidateMeshNoNegativeScale(pyblish.api.Validator):
    """Ensure that meshes don't have a negative scale."""

    order = openpype.api.ValidateContentsOrder
    hosts = ["blender"]
    families = ["model"]
    category = "geometry"
    label = "Mesh No Negative Scale"
    actions = [openpype.hosts.blender.api.action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance) -> List:
        invalid = []
        for obj in instance:
            if isinstance(obj, bpy.types.Object) and obj.type == 'MESH':
                if any(v < 0 for v in obj.scale):
                    invalid.append(obj)

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                f"Meshes found in instance with negative scale: {invalid}"
            )
