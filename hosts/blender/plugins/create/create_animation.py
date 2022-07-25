"""Create an animation asset."""

import bpy

from openpype.pipeline import legacy_io
from openpype.hosts.blender.api import plugin, lib, ops
from openpype.hosts.blender.api.pipeline import AVALON_INSTANCES


class CreateAnimation(plugin.Creator):
    """Animation output for character rigs"""

    name = "animationMain"
    label = "Animation"
    family = "animation"
    icon = "male"

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
        # name = self.name
        # if not name:
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)
        # asset_group = bpy.data.objects.new(name=name, object_data=None)
        # asset_group.empty_display_type = 'SINGLE_ARROW'
        asset_group = bpy.data.collections.new(name=name)
        instances.children.link(asset_group)
        self.data['task'] = legacy_io.Session.get('AVALON_TASK')
        lib.imprint(asset_group, self.data)

        if (self.options or {}).get("useSelection"):
            selected = lib.get_selection()
            for obj in selected:
                asset_group.objects.link(obj)
        elif (self.options or {}).get("asset_group"):
            obj = (self.options or {}).get("asset_group")
            asset_group.objects.link(obj)

        return asset_group
