from typing import List
import bpy
import pyblish.api
import openpype.hosts.blender.api.action
from openpype.hosts.blender.api import plugin


class ValidateNoColonsInName(pyblish.api.InstancePlugin):
    """There cannot be colons in names

    Object or bone names cannot include colons. Other software do not
    handle colons correctly.

    """

    order = openpype.api.ValidateContentsOrder
    hosts = ["blender"]
    families = ["model", "rig"]
    version = (0, 1, 0)
    label = "No Colons in names"
    actions = [openpype.hosts.blender.api.action.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance) -> List:
        invalid = []
        collection = bpy.data.collections[instance.name]
        objects = plugin.get_all_objects_in_collection(collection)
        for obj in [obj for obj in objects]:
            if ":" in obj.name:
                invalid.append(obj)
            if bpy.data.collections.get(obj.name) is None:
                if obj.type == "ARMATURE":
                    for bone in obj.data.bones:
                        if ":" in bone.name:
                            invalid.append(obj)
                            break
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(f"Objects found with colon in name: {invalid}")
