"""Create blender world asset."""
import bpy

from openpype.hosts.blender.api import plugin


class CreateWorld(plugin.Creator):
    """Create a Blender World instance."""

    name = "worldMain"
    label = "Blender World"
    family = "blender.world"
    icon = "earth"

    bl_types = frozenset({bpy.types.World})
