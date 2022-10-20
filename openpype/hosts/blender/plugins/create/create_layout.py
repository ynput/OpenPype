"""Create a layout asset."""
import bpy

from openpype.hosts.blender.api import plugin


class CreateLayout(plugin.Creator):
    """A grouped package of loaded content"""

    name = "layoutMain"
    label = "Layout"
    family = "layout"
    icon = "cubes"
    defaults = ["Main", "FromAnimation"]
    color_tag = "COLOR_02"
    bl_types = (bpy.types.Collection, bpy.types.Object)
