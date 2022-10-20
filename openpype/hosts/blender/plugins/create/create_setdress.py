"""Create a setdress asset."""
import bpy

from openpype.hosts.blender.api import plugin


class CreateSetdress(plugin.Creator):
    """A grouped package of loaded content"""

    name = "setdressMain"
    label = "Set Dress"
    family = "setdress"
    icon = "cubes"
    color_tag = "COLOR_06"
    bl_types = (bpy.types.Collection, bpy.types.Object)
