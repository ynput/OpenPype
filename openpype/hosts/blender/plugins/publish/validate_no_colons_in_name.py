from typing import List

import bpy

import pyblish.api
from openpype.api import ValidateContentsOrder
from openpype.hosts.blender.api.action import SelectInvalidAction


class ValidateNoColonsInName(pyblish.api.InstancePlugin):
    """There cannot be colons in names

    Object or bone names cannot include colons. Other software do not
    handle colons correctly.

    """

    order = ValidateContentsOrder
    hosts = ["blender"]
    families = ["model", "rig"]
    category = "cleanup"
    version = (0, 1, 0)
    label = "No Colons in names"
    actions = [SelectInvalidAction]

    @staticmethod
    def get_invalid(cls, instance) -> List:
        invalid = []
        for obj in set(instance):
            if ':' in obj.name:
                invalid.append(obj)
            if isinstance(obj, bpy.types.Object) and obj.type == 'ARMATURE':
                for bone in obj.data.bones:
                    if ':' in bone.name:
                        invalid.append(obj)
                        break
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                f"Objects found with colon in name: {invalid}")
