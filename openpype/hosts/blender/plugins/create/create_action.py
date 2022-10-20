"""Create an action asset."""

import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.lib import get_selection


class CreateAction(plugin.Creator):
    """Action output for character rigs"""

    name = "actionMain"
    label = "Action"
    family = "action"
    icon = "male"
    color_tag = "COLOR_07"
    bl_types = (bpy.types.Action,)

    def _use_selection(self, container):
        for obj in get_selection():
            if (
                obj.animation_data is not None
                and obj.animation_data.action is not None
            ):
                empty = bpy.data.objects.new(
                    name=container.name, object_data=None
                )
                empty.hide_viewport = True
                empty.animation_data_create()
                empty.animation_data.action = obj.animation_data.action
                empty.animation_data.action.name = container.name
                container.objects.link(empty)
