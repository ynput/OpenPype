from typing import List

import pyblish.api
import openpype.hosts.blender.api.action


class ValidateObjectIsInObjectMode(pyblish.api.InstancePlugin):
    """Validate that the objects in the instance are in Object Mode."""

    order = pyblish.api.ValidatorOrder - 0.01
    hosts = ["blender"]
    families = ["model", "rig", "layout"]
    category = "geometry"
    label = "Validate Object Mode"
    actions = [openpype.hosts.blender.api.action.SelectInvalidAction]
    optional = False

    @classmethod
    def get_invalid(cls, instance) -> List:
        invalid = []
        for obj in [obj for obj in instance]:
            try:
                if obj.type == 'MESH' or obj.type == 'ARMATURE':
                    # Check if the object is in object mode.
                    if not obj.mode == 'OBJECT':
                        invalid.append(obj)
            except Exception:
                continue
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                f"Object found in instance is not in Object Mode: {invalid}")
