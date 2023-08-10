"""Create render."""

import bpy

from openpype.pipeline import get_current_task_name
from openpype.hosts.blender.api import plugin, lib, ops
from openpype.hosts.blender.api.pipeline import AVALON_INSTANCES


class CreateRenderlayer(plugin.Creator):
    """Single baked camera"""

    name = "renderingMain"
    label = "Render"
    family = "renderlayer"
    icon = "eye"

    render_settings = {}

    def process(self):
        """ Run the creator on Blender main thread"""
        mti = ops.MainThreadItem(self._process)
        ops.execute_in_main_thread(mti)

    def _process(self):
        # Get Instance Container or create it if it does not exist
        instances = bpy.data.collections.get(AVALON_INSTANCES)
        if not instances:
            instances = bpy.data.collections.new(name=AVALON_INSTANCES)
            bpy.context.scene.collection.children.link(instances)

        # Create instance object
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)
        asset_group = bpy.data.collections.new(name=name)
        instances.children.link(asset_group)
        self.data['task'] = get_current_task_name()
        lib.imprint(asset_group, self.data)

        if (self.options or {}).get("useSelection"):
            selected = lib.get_selection()
            for obj in selected:
                asset_group.objects.link(obj)
        elif (self.options or {}).get("asset_group"):
            obj = (self.options or {}).get("asset_group")
            asset_group.objects.link(obj)

        return asset_group
