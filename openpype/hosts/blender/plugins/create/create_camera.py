"""Create a camera asset."""

import bpy

from openpype.hosts.blender.api import plugin


class CreateCamera(plugin.Creator):
    """Polygonal static geometry"""

    name = "cameraMain"
    label = "Camera"
    family = "camera"
    icon = "video-camera"

    def _process(self):
        # Get Instance Container
        container = super()._process()

        # Create instance object
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)

        camera = bpy.data.cameras.new(name)
        camera_obj = bpy.data.objects.new(name, camera)

        container.objects.link(camera_obj)

        return container
