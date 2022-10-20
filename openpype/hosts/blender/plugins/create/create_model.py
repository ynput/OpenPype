"""Create a model asset."""
import bpy

from openpype.hosts.blender.api import plugin


class CreateModel(plugin.Creator):
    """Polygonal static geometry"""

    name = "modelMain"
    label = "Model"
    family = "model"
    icon = "cube"
    defaults = ["Main", "Proxy"]
    color_tag = "COLOR_04"
    bl_types = (bpy.types.Collection, bpy.types.Object)
