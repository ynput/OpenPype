"""Create a layout asset."""

import bpy

from avalon import api
from openpype.hosts.blender.api import plugin, lib, ops
from openpype.hosts.blender.api.pipeline import AVALON_INSTANCES


class CreateLayout(plugin.Creator):
    """Layout output for character rigs"""

    name = "layoutMain"
    label = "Layout"
    family = "layout"
    icon = "cubes"

    def process(self):
        """Run the creator on Blender main thread"""
        mti = ops.MainThreadItem(self._process)
        ops.execute_in_main_thread(mti)

    def _process(self):
        # get info from data and create name value
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)

        # name = RIG_TASK_NAME
        containers = bpy.context.scene.collection.children

        # Get Instance Container or create it if it does not exist
        instance = bpy.data.collections.get(name)
        if not instance:
            instance = bpy.data.collections.new(name=name)
            bpy.context.scene.collection.children.link(instance)

        self.data["task"] = api.Session.get("AVALON_TASK")
        lib.imprint(instance, self.data)

        for container in containers:
            if instance.children.get(container.name) is None and instance != container:
                bpy.context.scene.collection.children.unlink(container)
                instance.children.link(container)

        # Add selected objects to instance
        objects_to_link = list()
        if (self.options or {}).get("useSelection"):
            objects_to_link = self.get_selection_hierarchie()
        else:
            objects_to_link = bpy.context.scene.collection.objects

        for obj in objects_to_link:
            if instance.get(obj.name) is None:
                instance.objects.link(obj)
            if bpy.context.scene.collection.objects.get(obj.name) is not None:
                bpy.context.scene.collection.objects.unlink(obj)
        return instance
