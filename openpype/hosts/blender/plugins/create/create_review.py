"""Create review."""
from typing import List

import bpy
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.properties import OpenpypeInstance

from openpype.hosts.blender.plugins.create.create_camera import _get_camera_from_datablocks


class CreateReview(plugin.Creator):
    """Review is basically a camera with different integration."""

    name = "reviewDefault"
    label = "Review"
    family = "review"
    icon = "video-camera"

    def process(
        self, datablocks: List[bpy.types.ID] = None, **kwargs
    ) -> OpenpypeInstance:
        """OVERRIDE from CreateCamera to not rename target camera.
        
        Still create one if None.
        """
        # Create instance object
        asset = self.data["asset"]
        subset = self.data["subset"]
        instance_name = plugin.build_op_basename(asset, subset)

        # Create camera if doesn't exist
        datablocks = datablocks or []
        camera = _get_camera_from_datablocks(datablocks)
        if not camera:
            camera = bpy.data.cameras.new(instance_name)
            camera_obj = bpy.data.objects.new(instance_name, camera)
            datablocks.append(camera_obj)

        # Create Instance
        return super().process(datablocks, **kwargs)
