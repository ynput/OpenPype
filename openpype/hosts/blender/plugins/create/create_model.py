"""Create a model asset."""

import bpy

from avalon import api
from openpype.hosts.blender.api import plugin, lib, ops


class CreateModel(plugin.Creator):
    """Polygonal static geometry"""

    name = "modelMain"
    label = "Model"
    family = "model"
    icon = "cube"

    def process(self):
        """Run the creator on Blender main thread"""
        mti = ops.MainThreadItem(self._process)
        ops.execute_in_main_thread(mti)

    def _process(self):
        # Get info from data and create name value
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)

        # Get the scene collection and all the collection in the scene
        scene_collection = bpy.context.scene.collection

        # Get Instance Container or create it if it does not exist
        container = bpy.data.collections.get(name)
        if not container:
            container = bpy.data.collections.new(name=name)
            scene_collection.children.link(container)

        # Add custom property on the instance container with the data
        self.data["task"] = api.Session.get("AVALON_TASK")
        lib.imprint(container, self.data)

        # Add selected objects to instance container
        if (self.options or {}).get("useSelection"):
            selected = lib.get_selection()
            for object in selected:
                container.objects.link(object)
                scene_collection.objects.unlink(object)
        else:
            objects = scene_collection.objects
            for object in objects:
                container.objects.link(object)
                scene_collection.objects.unlink(object)

        return container
