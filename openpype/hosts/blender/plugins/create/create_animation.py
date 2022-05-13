"""Create an animation asset."""

from openpype.hosts.blender.api import plugin


class CreateAnimation(plugin.Creator):
    """Animation output for character rigs"""

    name = "animationMain"
    label = "Animation"
    family = "animation"
    icon = "male"
    color_tag = "COLOR_01"
