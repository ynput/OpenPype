from typing import List

import bpy

import pyblish.api
import pype.hosts.blender.action


class ValidateMeshHasUvs(pyblish.api.InstancePlugin):
    """Validate that the current mesh has UV's."""

    order = pyblish.api.ValidatorOrder
    hosts = ["blender"]
    families = ["model"]
    category = "geometry"
    label = "Mesh Has UV's"
    actions = [pype.hosts.blender.action.SelectInvalidAction]
    optional = True

    @staticmethod
    def has_uvs(obj: bpy.types.Object) -> bool:
        """Check if an object has uv's."""
        if not obj.data.uv_layers:
            return False
        for uv_layer in obj.data.uv_layers:
            for polygon in obj.data.polygons:
                for loop_index in polygon.loop_indices:
                    if not uv_layer.data[loop_index].uv:
                        return False

        return True

    @classmethod
    def get_invalid(cls, instance) -> List:
        invalid = []
        # TODO (jasper): only check objects in the collection that will be published?
        for obj in [
            obj for obj in instance]:
            try:
                if obj.type == 'MESH':
                    # Make sure we are in object mode.
                    bpy.ops.object.mode_set(mode='OBJECT')
                    if not cls.has_uvs(obj):
                        invalid.append(obj)
            except:
                continue
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(f"Meshes found in instance without valid UV's: {invalid}")
