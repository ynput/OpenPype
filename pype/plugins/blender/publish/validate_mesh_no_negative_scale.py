from typing import List

import bpy

import pyblish.api
import pype.hosts.blender.action


class ValidateMeshNoNegativeScale(pyblish.api.Validator):
    """Ensure that meshes don't have a negative scale."""

    order = pyblish.api.ValidatorOrder
    hosts = ["blender"]
    families = ["model"]
    label = "Mesh No Negative Scale"
    actions = [pype.hosts.blender.action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance) -> List:
        invalid = []
        # TODO (jasper): only check objects in the collection that will be published?
        for obj in [
            obj for obj in bpy.data.objects if obj.type == 'MESH'
        ]:
            if any(v < 0 for v in obj.scale):
                invalid.append(obj)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                f"Meshes found in instance with negative scale: {invalid}"
            )
