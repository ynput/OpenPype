"""Create a Blender scene asset."""

import bpy

from openpype.pipeline import get_current_task_name
from openpype.hosts.blender.api import plugin, lib, ops
from openpype.hosts.blender.api.pipeline import AVALON_INSTANCES


class CreateBlendScene(plugin.Creator):
    """Generic group of assets"""

    name = "blendScene"
    label = "Blender Scene"
    family = "blendScene"
    icon = "cubes"

    maintain_selection = False

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

        # Create the new asset group as collection
        asset_group = bpy.data.collections.new(name=name)
        instances.children.link(asset_group)
        self.data['task'] = get_current_task_name()
        lib.imprint(asset_group, self.data)

        try:
            area = next(
                area for area in bpy.context.window.screen.areas
                if area.type == 'OUTLINER')
            region = next(
                region for region in area.regions
                if region.type == 'WINDOW')
        except StopIteration as e:
            raise RuntimeError("Could not find outliner. An outliner space "
                               "must be in the main Blender window.") from e

        with bpy.context.temp_override(
            window=bpy.context.window,
            area=area,
            region=region,
            screen=bpy.context.window.screen
        ):
            ids = bpy.context.selected_ids

        for id in ids:
            if isinstance(id, bpy.types.Collection):
                asset_group.children.link(id)
            elif isinstance(id, bpy.types.Object):
                asset_group.objects.link(id)

        return asset_group
