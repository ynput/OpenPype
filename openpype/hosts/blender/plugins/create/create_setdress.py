"""Create a model asset."""

from openpype.hosts.blender.api import plugin


class CreateModel(plugin.Creator):
    """A grouped package of loaded content"""

    name = "setdressMain"
    label = "Set Dress"
    family = "setdress"
    icon = "cubes"
    color_tag = "COLOR_06"
