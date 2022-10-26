"""Create a camera asset."""

import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.lib import get_selection


class CreateCamera(plugin.Creator):
    """Single baked camera"""

    name = "cameraMain"
    label = "Camera"
    family = "camera"
    icon = "video-camera"
    color_tag = "COLOR_05"
    bl_types = (bpy.types.Camera,)

    def _link_to_container_collection(self, container):
        cameras = [obj for obj in get_selection() if obj.type == "CAMERA"]
        plugin.link_to_collection(cameras, container)

    def _process(self):
        # Get Instance Container
        container = super()._process()

        # Create instance object
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)

        for obj in container.all_objects:
            if obj.type == "CAMERA":
                obj.name = name
                obj.data.name = name
                break
        else:
            camera = bpy.data.cameras.new(name)
            camera_obj = bpy.data.objects.new(name, camera)
            container.objects.link(camera_obj)

        return container
