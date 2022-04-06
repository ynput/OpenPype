from typing import List

import bpy

import pyblish.api
import openpype.hosts.blender.api.action
from openpype.hosts.blender.api import plugin


class ValidateMeshNoNegativeScale(pyblish.api.Validator):
    """Ensure that meshes don't have a negative scale."""

    order = pyblish.api.ValidatorOrder
    hosts = ["blender"]
    families = ["model"]
    label = "Mesh No Negative Scale"
    actions = [openpype.hosts.blender.api.action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance) -> List:
        invalid = []
        # TODO (jasper): only check objects in the collection that will be published?
        collection = bpy.data.collections[instance.name]
        objects = plugin.get_all_objects_in_collection(collection)
        for obj in [obj for obj in objects if obj.type == "MESH"]:
            if any(v < 0 for v in obj.scale):
                invalid.append(obj)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                f"Meshes found in instance with negative scale: {invalid}"
            )
