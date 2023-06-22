"""Create an animation asset."""
import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.utils import BL_OUTLINER_TYPES


class CreateAnimation(plugin.Creator):
    """Animation output for character rigs"""

    name = "animationMain"
    label = "Animation"
    family = "animation"
    icon = "male"
    bl_types = frozenset(BL_OUTLINER_TYPES | {bpy.types.Action})
