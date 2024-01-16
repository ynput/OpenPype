from typing import List

import bpy

import pyblish.api

from openpype.pipeline.publish import (
    ValidateContentsOrder,
    OptionalPyblishPluginMixin,
    PublishValidationError
)
import openpype.hosts.blender.api.action


class ValidateMeshHasUvs(
        pyblish.api.InstancePlugin,
        OptionalPyblishPluginMixin,
):
    """Validate that the current mesh has UV's."""

    order = ValidateContentsOrder
    hosts = ["blender"]
    families = ["model"]
    label = "Mesh Has UVs"
    actions = [openpype.hosts.blender.api.action.SelectInvalidAction]
    optional = True

    @staticmethod
    def has_uvs(obj: bpy.types.Object) -> bool:
        """Check if an object has uv's."""
        if not obj.data.uv_layers:
            return False
        for uv_layer in obj.data.uv_layers:
            for polygon in obj.data.polygons:
                for loop_index in polygon.loop_indices:
                    if (
                        loop_index >= len(uv_layer.data)
                        or not uv_layer.data[loop_index].uv
                    ):
                        return False

        return True

    @classmethod
    def get_invalid(cls, instance) -> List:
        invalid = []
        for obj in instance:
            if isinstance(obj, bpy.types.Object) and obj.type == 'MESH':
                if obj.mode != "OBJECT":
                    cls.log.warning(
                        f"Mesh object {obj.name} should be in 'OBJECT' mode"
                        " to be properly checked."
                    )
                if not cls.has_uvs(obj):
                    invalid.append(obj)
        return invalid

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                f"Meshes found in instance without valid UV's: {invalid}"
            )
