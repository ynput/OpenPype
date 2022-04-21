"""Create an animation asset."""

import bpy

from avalon import api
from openpype.hosts.blender.api import plugin, lib, ops, dialog


class CreateAnimation(plugin.Creator):
    """Animation output for character rigs"""

    name = "animationMain"
    label = "Animation"
    family = "animation"
    icon = "male"

    def _is_all_in_container(self):
        """ "
        Check if use selection option is checked
        """

        self.all_in_container = True
        # Get value of use_selection option
        if (self.options or {}).get("useSelection"):
            # If Selection is not empty
            if not lib.get_selection():
                # Show a dialog to know if we take all the scene
                # Set the answer in all_in_container
                self.all_in_container = dialog.use_selection_behaviour_dialog()
            # If Selection is empty
            else:
                # Set all_in_container to false
                self.all_in_container = False
        return self.all_in_container

    def _is_an_avalon_container(self, collection):
        """
        Check if the collection is an avalon container
        """
        return plugin.is_avalon_container(
            collection
        ) or plugin.is_pyblish_avalon_container(collection)

    def _is_local_container(self, collection):
        """
        Check if the container is local
        """
        return not (
            plugin.is_avalon_container(collection)
            or plugin.is_pyblish_avalon_container(collection)
        )

    def _search_lone_collection(self):
        """ "
        search if a collection can be rename and use like a container
        """
        if len(self.scene_collection.children) == 1:
            lone_collection = self.scene_collection.children[0]
            if self._is_local_container(lone_collection):
                if not self._is_an_avalon_container(lone_collection):
                    return lone_collection
        return None

    def _get_collections_with_all_objects_selected(self):
        """
        Check if some collection have all objects selected and return them
        """
        collections_to_copy = list()
        # Loop on all the data collections
        objects_selected = self.objects_selected.copy()

        for collection in bpy.data.collections.values():
            all_object_in_collection = plugin.get_all_objects_in_collection(
                collection
            )
            # If the selected objects is in the collection
            if (
                all(
                    item in objects_selected
                    for item in all_object_in_collection
                )
                and collection.objects.values()
            ):
                # Then append the collection in the collections_to_copy
                collections_to_copy.append(collection)
                # And remove the collection objects of the selected objects
                for object in all_object_in_collection:
                    if object in self.objects_selected:
                        self.objects_selected.remove(object)

        # Remove collection if it is in another one
        # make a copy of the list to keep thzm when objects are remove
        # from the original
        collections_to_copy_duplicate = collections_to_copy.copy()
        # Loop on the collections to copy
        for collection_to_copy in collections_to_copy_duplicate:
            # Get All the collection in the collection to copy
            collections_in_collection = (
                plugin.get_all_collections_in_collection(collection_to_copy)
            )
            # Loop again on the collections to copy
            for collection_to_copy_current in collections_to_copy_duplicate:
                # And remove the collection_to_copy
                # which are in another collection_to_copy
                if collection_to_copy_current in collections_in_collection:
                    if collection_to_copy_current in collections_to_copy:
                        collections_to_copy.remove(collection_to_copy_current)
        return collections_to_copy

    def _create_container(self, name):
        """
        Create the container with the given name
        """
        # Search in the container already exists
        container = bpy.data.collections.get(name)
        # If Container doesn't exist create it
        if container is None:
            container = bpy.data.collections.new(name=name)
            plugin.link_collection_to_collection(
                container, self.scene_collection
            )
        # Else show a dialog box which say that the container already exist
        else:
            dialog.container_already_exist_dialog()
            return None
        return container

    def _link_objects_in_container(self, objects, container):
        """
        link the objects given to the container
        """
        for object in objects:
            if object not in container.objects.values():
                plugin.link_object_to_collection(object, container)

    def _link_collections_in_container(self, collections, container):
        """
        link the collections given to the container
        """
        for collection in collections:
            # If the collection is not yet in the container
            # And is not the container
            if (
                collection not in container.children.values()
                and collection is not container
            ):
                # Link them to the container
                plugin.link_collection_to_collection(collection, container)

    def _link_all_in_container(self, container):
        """
        link all the scene to the container
        """

        # If all the collection isn't already in the container
        if len(self.scene_collection.children) != 1:
            # Get collections under the scene collection
            collections = self.scene_collection.children
            self._link_collections_in_container(collections, container)

        # Get objects under the scene collection
        objects = self.scene_collection.objects
        self._link_objects_in_container(objects, container)

    def _link_selection_in_container(self, container):
        """
        link the selection to the container
        """
        # Get collections with all objects selected first because
        # if they exist their objects will be removed from the selection
        collections_to_copy = self._get_collections_with_all_objects_selected()
        self._link_objects_in_container(self.objects_selected, container)
        self._link_collections_in_container(collections_to_copy, container)

    def process(self):
        """Run the creator on Blender main thread"""
        mti = ops.MainThreadItem(self._process)
        ops.execute_in_main_thread(mti)

    def _process(self):

        self.scene_collection = bpy.context.scene.collection

        all_in_container = self._is_all_in_container()

        # Get info from data and create name value
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)

        # check if a lone collection is at the root of the scene
        lone_collection = self._search_lone_collection()

        # Create the container
        container = self._create_container(name)
        if container is None:
            return

        # Add custom property on the instance container with the data
        self.data["task"] = api.Session.get("AVALON_TASK")
        lib.imprint(container, self.data)

        # Fill the Container with all the scene or the selection
        self.objects_selected = lib.get_selection()
        if all_in_container:
            self._link_all_in_container(container)
        else:
            self._link_selection_in_container(container)

        # Remove the lone collection in container
        # But keep its contain
        if lone_collection in container.children.values():
            for collection in lone_collection.children.values():
                plugin.link_collection_to_collection(collection, container)
            for object in lone_collection.objects.values():
                plugin.link_object_to_collection(object, container)
            container.children.unlink(lone_collection)

        # If the container is empty remove them
        if not container.objects and not container.children:
            bpy.data.collections.remove(container)
        return container
