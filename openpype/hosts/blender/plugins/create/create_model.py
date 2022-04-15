"""Create a model asset."""
import bpy
from avalon import api
from openpype.hosts.blender.api import plugin, lib, ops, dialog


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
        all_in_container = True
        # Dialog box if use_selection is checked
        if (self.options or {}).get("useSelection"):
            # and not any objects selected
            if not lib.get_selection():
                all_in_container = dialog.use_selection_behaviour_dialog()
            # if any objects is selected
            # not set all the objects in the container
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
        if container is None:
            is_avalon_container = False
            if len(scene_collection.children) == 1:
                is_avalon_container = plugin.is_avalon_container(
                    scene_collection.children[0]
                )
            if (
                len(scene_collection.children) == 1
                and all_in_container
                and not is_avalon_container
            ):
                container = scene_collection.children[0]
                container.name = name
            else:
                container = bpy.data.collections.new(name=name)
                plugin.link_collection_to_collection(
                    container, scene_collection
                )

        # Add custom property on the instance container with the data
        self.data["task"] = api.Session.get("AVALON_TASK")
        lib.imprint(container, self.data)

        # Add selected objects to container
        # If all_in_container is true set all the objects in the container
        if all_in_container:
            # If all the collection isn't already in the container
            if len(scene_collection.children) != 1:
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
                        if collection in scene_collection.children.values():
                            scene_collection.children.unlink(collection)
                        plugin.link_collection_to_collection(
                            collection, container
                        )

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
                    plugin.link_collection_to_collection(object, container)

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
                    plugin.link_object_to_collection(object, container)
        # If the container is empty remove them
        if not container.objects and not container.children:
            bpy.data.collections.remove(container)
        return container
