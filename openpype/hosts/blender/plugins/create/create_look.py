"""Create a lookdev asset."""
import bpy

from openpype.hosts.blender.api import plugin


class CreateLook(plugin.Creator):
    """Lookdev for geometries"""

    name = "lookMain"
    label = "Lookdev"
    family = "look"
    icon = "paint-brush"

    bl_types = frozenset({bpy.types.Material, bpy.types.Object})
