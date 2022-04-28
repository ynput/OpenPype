"""Create a layout asset."""

from openpype.hosts.blender.api import plugin


class CreateLayout(plugin.Creator):
    """Layout output for character rigs"""

    name = "layoutMain"
    label = "Layout"
    family = "layout"
    icon = "cubes"
