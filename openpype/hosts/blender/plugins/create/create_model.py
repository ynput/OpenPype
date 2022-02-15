"""Create a model asset."""

import bpy

from avalon import api
from openpype.hosts.blender.api import plugin, lib, ops
from openpype.hosts.blender.api.pipeline import AVALON_INSTANCES


class CreateModel(plugin.Creator):
    """Polygonal static geometry"""

    name = "modelMain"
    label = "Model"
    family = "model"
    icon = "cube"

    def process(self):
        """ Run the creator on Blender main thread"""
        mti = ops.MainThreadItem(self._process)
        ops.execute_in_main_thread(mti)

    def _process(self):


        # Create instance object
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)

        # Get Instance Container or create it if it does not exist

        #asset_group = bpy.data.objects.new(name=name, object_data=None)
        #asset_group.empty_display_type = 'SINGLE_ARROW'

        #instance = bpy.data.collections.get(name)
        instance = bpy.data.objects.get(name)
        if not instance:
            instance = bpy.data.objects.new(name=name, object_data=None)
            instance.empty_display_type = 'SINGLE_ARROW'
        bpy.context.scene.collection.objects.link(instance)

        self.data['task'] = api.Session.get('AVALON_TASK')
        lib.imprint(instance, self.data)

        # Add selected objects to instance
        if (self.options or {}).get("useSelection"):
            bpy.context.view_layer.objects.active = instance
            selected = lib.get_selection()
            for obj in selected:
                obj.select_set(True)
            selected.append(instance)
            bpy.ops.object.parent_set(keep_transform=True)
        return instance
