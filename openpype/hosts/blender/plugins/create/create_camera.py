"""Create a camera asset."""

import bpy

from avalon import api
from openpype.hosts.blender.api import plugin, lib, ops
from openpype.hosts.blender.api.pipeline import AVALON_INSTANCES


class CreateCamera(plugin.Creator):
    """Polygonal static geometry"""

    name = "cameraMain"
    label = "Camera"
    family = "camera"
    icon = "video-camera"

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
        if container is None:
            container = bpy.data.collections.new(name=name)
            plugin.link_collection_to_collection(container, scene_collection)

        camera = bpy.data.cameras.new(subset)
        camera_object = bpy.data.objects.new(subset, camera)
        plugin.link_object_to_collection(camera_object, container)
        # Add custom property on the instance container with the data
        self.data["task"] = api.Session.get("AVALON_TASK")
        lib.imprint(container, self.data)

        # If all_in_container is False set selected objects in the container
        if (self.options or {}).get("useSelection"):
            selected = lib.get_selection()
            for object in selected:
                if object not in container.objects.values():
                    # Find the users collection of the object
                    for collection in object.users_collection:
                        # And unlink the object to its users collection
                        collection.objects.unlink(object)
                    # Link the object to the container
                    plugin.link_item_to_objects(object, container)
        # If the container is empty remove them
        if not container.objects and not container.children:
            bpy.data.collections.remove(container)
        return container
