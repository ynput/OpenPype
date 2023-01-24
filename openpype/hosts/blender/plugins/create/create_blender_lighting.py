"""Create blender lighting instance.

Lighting may contain light objects but also geometry for combobox or rigs,
and a word.
"""
import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.utils import BL_OUTLINER_TYPES


class CreateLighting(plugin.Creator):
    """Create a Blender Lighting instance."""

    name = "worldMain"
    label = "Blender Lighting"
    family = "blender.lighting"
    icon = "lightbulb-o"

    bl_types = frozenset(BL_OUTLINER_TYPES | {bpy.types.World})
