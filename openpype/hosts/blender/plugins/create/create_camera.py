"""Create a camera asset."""

from typing import List
import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.properties import OpenpypeInstance


class CreateCamera(plugin.Creator):
    """Single baked camera"""

    name = "cameraMain"
    label = "Camera"
    family = "camera"
    icon = "video-camera"

    @plugin.exec_process
    def process(
        self, datablocks: List[bpy.types.ID] = None
    ) -> OpenpypeInstance:
        # Create instance object
        asset = self.data["asset"]
        subset = self.data["subset"]
        instance_name = plugin.build_op_basename(asset, subset)

        # Rename existing camera or create one
        for obj in datablocks:
            if obj and obj.type == "CAMERA":
                obj.name = instance_name
                obj.data.name = instance_name
                break
        else:
            camera = bpy.data.cameras.new(instance_name)
            camera_obj = bpy.data.objects.new(instance_name, camera)
            datablocks.append(camera_obj)

        # Create Instance
        return super().process(datablocks)
