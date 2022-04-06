"""Create a layout asset."""

import bpy

from avalon import api
from openpype.hosts.blender.api import plugin, lib, ops, dialog


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
        # If all_in_container is true set all the objects in the container
        if all_in_container:
            for collection in collections:
                # if collection is not yet in the container
                # And is not the container
                if (
                    container.children.get(collection.name) is None
                    and container is not collection
                ):
                    scene_collection.children.unlink(collection)
                    container.children.link(collection)

        # Add selected objects to container
        objects_to_link = list()
        # If the use selection option is checked
        if all_in_container:
            # Append object in the scene collection
            # In the objects_to_link list
            objects_to_link = scene_collection.objects
        else:
            selected = lib.get_selection()
            for object in selected:
                # Append object selected in the objects_to_link list
                objects_to_link.append(object)
        # If the use selection option is not checked

        for object in objects_to_link:
            # If the object is not yet in the container
            if object not in container.objects.values():
                # Find the users collection of the object
                for collection in object.users_collection:
                    # And unlink the object to his users collection
                    collection.objects.unlink(object)
                # Link the object to the container
                container.objects.link(object)
                # If the container is empty romove them
        if not container.objects and not container.children:
            bpy.data.collections.remove(container)
        return container
