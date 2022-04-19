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

    def _is_all_in_container(self):
        """ "
        Check if use selection option is checked
        """
        self.all_in_container = True
        if (self.options or {}).get("useSelection"):
            if not lib.get_selection():
                self.all_in_container = dialog.use_selection_behaviour_dialog()
            else:
                self.all_in_container = False
        return self.all_in_container

    def _search_lone_collection_in_scene(self):
        """ "
        search if a collection can be rename and use like a container
        """
        scene_collection = bpy.context.scene.collection
        is_avalon_container = False
        if len(scene_collection.children) == 1:
            is_avalon_container = plugin.is_avalon_container(
                scene_collection.children[0]
            )
        if len(scene_collection.children) == 1 and not is_avalon_container:
            return scene_collection.children[0]

    def _get_collections_with_all_objects_selected(self):
        """
        Check if some collection have all objects selected and return them
        """
        objects_selected = lib.get_selection()
        collections_to_copy = list()
        for collection in bpy.data.collections.values():
            all_object_in_collection = True
            if not collection.objects.values():
                all_object_in_collection = False
            for object in collection.objects.values():
                if object not in objects_selected:
                    all_object_in_collection = False
            if all_object_in_collection:
                collections_to_copy.append(collection)
                for object in collection.objects.values():
                    objects_selected.remove(object)
        return collections_to_copy

    def _create_container(self, name):
        """
        Create the container with the given name
        """
        # Get the scene collection and all the collection in the scene
        scene_collection = bpy.context.scene.collection

        # Get Instance Container or create it if it does not exist
        container = bpy.data.collections.get(name)
        if container is None:
            lone_collection = self._search_lone_collection_in_scene()
            collection_with_all_objects_selected = (
                self._get_collections_with_all_objects_selected()
            )

            is_avalon_container = False
            is_container_created = False

            if lone_collection is not None:
                is_avalon_container = plugin.is_avalon_container(
                    lone_collection
                ) or plugin.is_pyblish_avalon_container(lone_collection)

                if (
                    lone_collection.override_library is None
                    and lone_collection.library is None
                    and not is_avalon_container
                ):
                    if self.all_in_container:
                        container = lone_collection
                        container.name = name
                        is_container_created = True

                    if (
                        len(collection_with_all_objects_selected) == 1
                        and not is_container_created
                    ):
                        if (
                            collection_with_all_objects_selected[0]
                            == lone_collection
                        ):
                            container = lone_collection
                            container.name = name
                            is_container_created = True

            if not is_container_created:
                container = bpy.data.collections.new(name=name)
                plugin.link_collection_to_collection(
                    container, scene_collection
                )
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
                # Find the users collection of the object
                for collection in object.users_collection:
                    # And unlink the object to its users collection
                    collection.objects.unlink(object)
                # Link the object to the container
                plugin.link_object_to_collection(object, container)

    def _link_collections_in_container(self, collections, container):
        """
        link the collections given to the container
        """
        scene_collection = bpy.context.scene.collection
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
                plugin.link_collection_to_collection(collection, container)

    def _link_all_in_container(self, container):
        """
        link all the scene to the container
        """
        scene_collection = bpy.context.scene.collection
        # If all the collection isn't already in the container
        if len(scene_collection.children) != 1:
            # Get collections under the scene collection
            collections = scene_collection.children
            self._link_collections_in_container(collections, container)

        # Get objects under the scene collection
        objects = scene_collection.objects
        self._link_objects_in_container(objects, container)

    def _link_selection_in_container(self, container):
        """
        link the selection to the container
        """
        objects_selected = lib.get_selection()
        collections_to_copy = self._get_collections_with_all_objects_selected()
        self._link_objects_in_container(objects_selected, container)
        self._link_collections_in_container(collections_to_copy, container)

    def process(self):
        """Run the creator on Blender main thread"""
        mti = ops.MainThreadItem(self._process)
        ops.execute_in_main_thread(mti)

    def _process(self):
        all_in_container = self._is_all_in_container()

        # Get info from data and create name value
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)

        container = self._create_container(name)
        if container is None:
            return

        # Add custom property on the instance container with the data
        self.data["task"] = api.Session.get("AVALON_TASK")
        lib.imprint(container, self.data)

        if all_in_container:
            self._link_all_in_container(container)

        else:
            self._link_selection_in_container(container)

        # If the container is empty remove them
        if not container.objects and not container.children:
            bpy.data.collections.remove(container)
        return container
