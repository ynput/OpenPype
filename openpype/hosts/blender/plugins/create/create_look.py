"""Create a lookdev asset."""

from openpype.hosts.blender.api import plugin


class CreateLook(plugin.Creator):
    """Lookdev for geometries"""

    name = "lookMain"
    label = "Lookdev"
    family = "look"
    icon = "paint-brush"
    color_tag = "COLOR_07"
