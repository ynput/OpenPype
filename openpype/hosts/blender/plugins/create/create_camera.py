"""Create a camera asset."""

import bpy

from avalon import api
from openpype.hosts.blender.api import plugin, lib, ops, dialog
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
        all_in_container = True
        # Dialog box if use_selection is checked
        if (self.options or {}).get("useSelection"):
            # and not any objects selected
            if not lib.get_selection():
                all_in_container = dialog.use_selection_behaviour_dialog()
            # if any objects is selected not set all the objects in the container
            else:
                all_in_container = False

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

        camera = bpy.data.cameras.new(subset)
        camera_object = bpy.data.objects.new(subset, camera)
        container.objects.link(camera_object)
        # Add custom property on the instance container with the data
        self.data["task"] = api.Session.get("AVALON_TASK")
        lib.imprint(container, self.data)

        # Add selected objects to container
        # If all_in_container is true set all the objects in the container
        if all_in_container:
            # Get collections under the scene collection
            collections = scene_collection.children
            for collection in collections:
                # If the collection is not yet in the container
                # And is not the container
                if (
                    collection not in container.children.values()
                    and collection is not container
                ):
                    # Unlink the collection to the scene collection
                    # And link them to the container
                    scene_collection.children.unlink(collection)
                    container.children.link(collection)
            # Get objects under the scene collection
            objects = scene_collection.objects
            for object in objects:
                # If the object is not yet in the container
                if object not in container.objects.values():
                    # Find the users collection of the object
                    for user_collection in object.users_collection:
                        # And unlink the object to its users collection
                        user_collection.objects.unlink(object)
                    # Link the object to the container
                    container.objects.link(object)
        # If all_in_container is False set selected objects in the container
        else:
            selected = lib.get_selection()
            for object in selected:
                if object not in container.objects.values():
                    # Find the users collection of the object
                    for collection in object.users_collection:
                        # And unlink the object to its users collection
                        collection.objects.unlink(object)
                    # Link the object to the container
                    container.objects.link(object)
        # If the container is empty remove them
        if not container.objects and not container.children:
            bpy.data.collections.remove(container)
        return container
