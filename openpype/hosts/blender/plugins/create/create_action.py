"""Create an animation asset."""

import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.lib import get_selection


class CreateAction(plugin.Creator):
    """Action output for character rigs"""

    name = "actionMain"
    label = "Action"
    family = "action"
    icon = "male"

    def process(self):

        use_selection = False
        if self.options:
            use_selection = self.options.pop("useSelection", False)

        container = super()._process()

        if use_selection:
            for obj in get_selection():
                if (
                    obj.animation_data is not None
                    and obj.animation_data.action is not None
                ):
                    empty = bpy.data.objects.new(
                        name=container.name, object_data=None
                    )
                    empty.animation_data_create()
                    empty.animation_data.action = obj.animation_data.action
                    empty.animation_data.action.name = container.name
                    container.objects.link(empty)

        return container
