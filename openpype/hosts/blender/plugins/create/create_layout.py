"""Create a layout asset."""

from openpype.hosts.blender.api import plugin


class CreateLayout(plugin.Creator):
    """A grouped package of loaded content"""

    name = "layoutMain"
    label = "Layout"
    family = "layout"
    icon = "cubes"
    color_tag = "COLOR_02"
