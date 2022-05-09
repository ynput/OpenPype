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
