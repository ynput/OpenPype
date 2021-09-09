from typing import List

import mathutils

import pyblish.api
import openpype.hosts.blender.api.action


class ValidateTransformZero(pyblish.api.InstancePlugin):
    """Transforms can't have any values

    To solve this issue, try freezing the transforms. So long
    as the transforms, rotation and scale values are zero,
    you're all good.

    """

    order = openpype.api.ValidateContentsOrder
    hosts = ["blender"]
    families = ["model"]
    category = "geometry"
    version = (0, 1, 0)
    label = "Transform Zero"
    actions = [openpype.hosts.blender.api.action.SelectInvalidAction]

    _identity = mathutils.Matrix()

    @classmethod
    def get_invalid(cls, instance) -> List:
        invalid = []
        for obj in [obj for obj in instance]:
            if obj.matrix_basis != cls._identity:
                invalid.append(obj)
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                f"Object found in instance is not in Object Mode: {invalid}")
