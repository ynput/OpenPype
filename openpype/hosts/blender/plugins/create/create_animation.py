"""Create an animation asset."""
import bpy

from openpype.hosts.blender.api import plugin


class CreateAnimation(plugin.Creator):
    """Animation output for character rigs"""

    name = "animationMain"
    label = "Animation"
    family = "animation"
    icon = "male"
    bl_types = frozenset({bpy.types.Action, bpy.types.Object})
