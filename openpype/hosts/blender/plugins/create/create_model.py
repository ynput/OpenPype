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
        # If the use selection option is checked
        if (self.options or {}).get("useSelection"):
            selected = lib.get_selection()
            for object in selected:
                if object not in container.objects.values():
                    # Find the users collection of the object
                    for collection in object.users_collection:
                        # And unlink the object to his users collection
                        collection.objects.unlink(object)
                    # Link the object to the container
                    container.objects.link(object)
        # If the use selection option is not checked
        else:
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
                        # And unlink the object to his users collection
                        user_collection.objects.unlink(object)
                    # Link the object to the container
                    container.objects.link(object)
        return container
