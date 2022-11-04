"""Create a rig asset."""
import bpy

from openpype.hosts.blender.api import plugin


class CreateRig(plugin.Creator):
    """Artist-friendly rig with controls to direct motion"""

    name = "rigMain"
    label = "Rig"
    family = "rig"
    icon = "wheelchair"
    defaults = ["Main", "Proxy"]
    color_tag = "COLOR_03"
    bl_types = frozenset({bpy.types.Armature})
