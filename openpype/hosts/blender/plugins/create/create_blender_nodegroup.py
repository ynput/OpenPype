"""Create a blender nodegroup asset."""

from openpype.hosts.blender.api import plugin


class CreateBlenderNodegroup(plugin.Creator):
    """A grouped package of loaded content"""

    name = "blenderNodegroupMain"
    label = "Blender Nodegroup"
    family = "blender_nodegroud"
    icon = "microchip"
    color_tag = "COLOR_06"
