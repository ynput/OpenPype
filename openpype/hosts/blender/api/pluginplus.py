"""Shared functionality for pipeline plugins for Blender."""

import bpy

from .container import (
    get_all_objects_in_collection,
    get_all_collections_in_collection,
)


def link_collection_to_collection(collection_to_link, collection):
    """link an item to a collection"""
    if collection_to_link not in collection.children.values():
        collection.children.link(collection_to_link)


def link_objects_to_collection(objects, collection):
    """link an objects to a collection"""
    for obj in objects:
        if obj not in collection.objects.values():
            collection.objects.link(obj)


def is_pyblish_avalon_container(container):
    is_pyblish_avalon_container = False
    if container.get("avalon"):
        if container["avalon"].get("id") == "pyblish.avalon.container":
            is_pyblish_avalon_container = True
    return is_pyblish_avalon_container


def is_avalon_container(container):
    is_pyblish_avalon_container = False
    if container.get("avalon"):
        if container["avalon"].get("id") == "pyblish.avalon.instance":
            is_pyblish_avalon_container = True
    return is_pyblish_avalon_container


def is_an_avalon_container(collection):
    """
    Check if the collection is an avalon container
    """
    return is_avalon_container(
        collection
    ) or is_pyblish_avalon_container(collection)


def is_local_container(collection):
    """
    Check if the container is local
    """
    return not (
        is_avalon_container(collection)
        or is_pyblish_avalon_container(collection)
    )


def search_lone_collection():
    """ "
    search if a collection can be rename and use like a container
    """
    if len(bpy.context.scene.collection.children) == 1:
        lone_collection = bpy.context.scene.collection.children[0]
        if is_local_container(lone_collection):
            if not is_an_avalon_container(lone_collection):
                return lone_collection
    return None


def get_collections_with_all_objects_selected(objects_selected):
    """
    Check if some collection have all objects selected and return them
    """
    collections_to_copy = list()

    objects_selected = objects_selected.copy()
    # Loop on all the data collections
    for collection in bpy.data.collections.values():
        all_object_in_collection = get_all_objects_in_collection(
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
                if object in objects_selected:
                    objects_selected.remove(object)

    # Remove collection if it is in another one
    # make a copy of the list to keep thzm when objects are remove
    # from the original
    collections_to_copy_duplicate = list(collections_to_copy)
    # Loop on the collections to copy
    for collection_to_copy in collections_to_copy_duplicate:
        # Get All the collection in the collection to copy
        collections_in_collection = (
            get_all_collections_in_collection(collection_to_copy)
        )
        # Loop again on the collections to copy
        for collection_to_copy_current in collections_to_copy_duplicate:
            # And remove the collection_to_copy
            # which are in another collection_to_copy
            if collection_to_copy_current in collections_in_collection:
                if collection_to_copy_current in collections_to_copy:
                    collections_to_copy.remove(collection_to_copy_current)
    return collections_to_copy
