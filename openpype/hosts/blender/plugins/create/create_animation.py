"""Create an animation asset."""

import bpy

from avalon import api
from openpype.hosts.blender.api import plugin, lib, ops
from openpype.hosts.blender.api.pipeline import AVALON_INSTANCES


class CreateAnimation(plugin.Creator):
    """Animation output for character rigs"""

    name = "animationMain"
    label = "Animation"
    family = "animation"
    icon = "male"

    def process(self):
        """Run the creator on Blender main thread"""
        mti = ops.MainThreadItem(self._process)
        ops.execute_in_main_thread(mti)

    def _process(self):
        # Get Instance Container or create it if it does not exist
        # Get info from data and create name value
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)

        # Get the scene collection and all the collection in the scene
        scene_collection = bpy.context.scene.collection
        collections = scene_collection.children

        # Get Instance Container or create it if it does not exist
        container = bpy.data.collections.get(name)
        if not container:
            container = bpy.data.collections.new(name=name)
            scene_collection.children.link(container)

        # Add custom property on the instance container with the data
        self.data["task"] = api.Session.get("AVALON_TASK")
        lib.imprint(container, self.data)

        # Link the collections in the scene to the container
        for collection in collections:
            if (
                container.children.get(collection.name) is None
                and container != collection
            ):
                scene_collection.children.unlink(collection)
                container.children.link(collection)

        # Add selected objects to instance
        objects_to_link = list()
        if (self.options or {}).get("useSelection"):
            objects_to_link = self.get_selection_hierarchie()
        else:
            objects_to_link = scene_collection.objects

        for object in objects_to_link:
            if container.get(object.name) is None:
                container.objects.link(object)
            if scene_collection.objects.get(object.name) is not None:
                scene_collection.objects.unlink(object)
        return container
