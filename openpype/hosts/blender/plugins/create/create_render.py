"""Create a Render asset."""

from openpype.hosts.blender.api import plugin


class CreateLook(plugin.Creator):
    """Create Render instance"""

    name = "RenderMain"
    label = "Render"
    family = "render"
    icon = "eye"
