"""Create review."""

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
