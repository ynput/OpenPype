from typing import List

import mathutils
import bpy

import pyblish.api

import openpype.hosts.blender.api.action
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    OptionalPyblishPluginMixin,
    PublishValidationError
)


class ValidateTransformZero(pyblish.api.InstancePlugin,
                            OptionalPyblishPluginMixin):
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
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            names = ", ".join(obj.name for obj in invalid)
            raise PublishValidationError(
                "Objects found in instance which do not"
                f" have transform set to zero: {names}"
            )
