"""Create review."""

import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.lib import get_selection


class CreateReview(plugin.Creator):
    """Single baked camera"""

    name = "reviewDefault"
    label = "Review"
    family = "review"
    icon = "video-camera"
    color_tag = "COLOR_07"

    def _use_selection(self, container):
        selected_objects = set(get_selection())
        plugin.link_to_collection(selected_objects, container)

    def _process(self):
        # Get Instance Container
        container = super()._process()

        # Create camera if not get with use_selection.
        for obj in container.all_objects:
            if obj.type == "CAMERA":
                break
        else:
            asset = self.data["asset"]
            subset = self.data["subset"]
            name = plugin.asset_name(asset, subset)
            camera = bpy.data.cameras.new(name)
            camera_obj = bpy.data.objects.new(name, camera)
            container.objects.link(camera_obj)

        return container
