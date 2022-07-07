from typing import List

import bpy

import pyblish.api
from openpype.api import ValidateContentsOrder
from openpype.hosts.blender.api.action import SelectInvalidAction


class ValidateMaterialSlots(pyblish.api.InstancePlugin):
    """Validate that the objects have material slots linked with mode
    'OBJECT' and not 'DATA'.
    """

    order = ValidateContentsOrder
    hosts = ["blender"]
    families = ["look"]
    category = "geometry"
    label = "Validate Material Slots"
    actions = [SelectInvalidAction]
    optional = True

    @staticmethod
    def get_invalid(instance) -> List:
        invalid = []
        for obj in set(instance):
            if isinstance(obj, bpy.types.Object) and obj.type == 'MESH':
                for mtl_slot in obj.material_slots:
                    if mtl_slot.link == "DATA":
                        invalid.append(obj)
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                "Object found with some material slots"
                f"linked to this data: {invalid}"
            )
