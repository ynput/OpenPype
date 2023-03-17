from typing import List

import mathutils
import bpy

import pyblish.api

import openpype.hosts.blender.api.action
from openpype.pipeline.publish import ValidateContentsOrder


class ValidateTransformZero(pyblish.api.InstancePlugin):
    """Transforms can't have any values

    To solve this issue, try freezing the transforms. So long
    as the transforms, rotation and scale values are zero,
    you're all good.

    """

    order = ValidateContentsOrder
    hosts = ["blender"]
    families = ["model"]
    label = "Transform Zero"
    actions = [openpype.hosts.blender.api.action.SelectInvalidAction]

    _identity = mathutils.Matrix()

    @classmethod
    def get_invalid(cls, instance) -> List:
        invalid = []
        for obj in instance:
            if (
                isinstance(obj, bpy.types.Object)
                and obj.matrix_basis != cls._identity
            ):
                invalid.append(obj)
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                "Object found in instance has not"
                f" transform to zero: {invalid}"
            )
