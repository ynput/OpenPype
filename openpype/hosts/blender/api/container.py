"""Shared container functionality for pipeline plugins for Blender."""
import bpy

from typing import Optional

from .pipeline import AVALON_PROPERTY


__all__ = [
    "remove_container",
    "remove_orphan_datablocks",
    "link_collection_to_collection",
    "link_object_to_collection",
    "set_fake_user_on_orphans",
    "remove_fake_user_on_orphans",
    "model_asset_name",
    "get_parent_collections",
    "get_container_collections",
    "set_original_name_for_objects_container",
    "set_temp_namespace_for_objects_container",
    "remove_namespace_for_objects_container",
    "get_containers_list",
    "get_all_collections_in_collection",
    "get_all_objects_in_collection",
    "get_model_unique_number",
    "is_local_collection",
    "is_pyblish_avalon_container",
    "is_avalon_container",
]

property_names = [
    "actions",
    "armatures",
    "brushes",
    "cameras",
    "collections",
    "curves",
    "grease_pencils",
    "images",
    "lattices",
    "libraries",
    "lightprobes",
    "lights",
    "linestyles",
    "masks",
    "materials",
    "meshes",
    "metaballs",
    "movieclips",
    "node_groups",
    "objects",
    "paint_curves",
    "palettes",
    "particles",
    "shape_keys",
    "sounds",
    "texts",
    "textures",
    "volumes",
]


def remove_container(container):
    items_with_fake_user_list = set_fake_user_on_orphans()
    objects = get_all_objects_in_collection(container)
    for obj in objects:
        bpy.data.objects.remove(obj)

    collections = get_all_collections_in_collection(container)
    for collection in collections:
        bpy.data.collections.remove(collection)

    # Remove the container
    bpy.data.collections.remove(container)
    remove_orphan_datablocks()
    remove_fake_user_on_orphans(items_with_fake_user_list)


def remove_orphan_datablocks():
    """Remove the data_blocks without users"""

    orphan_block_users_find = True
    while orphan_block_users_find:
        orphan_block_users_find = False
        properties = property_names.copy()

        for prop in properties:
            data = getattr(bpy.data, prop)
            for block in data:
                if block.users == 0 and not block.use_fake_user:
                    orphan_block_users_find = True
                    data.remove(block)

        for block in bpy.data.libraries:
            if not block.users_id and not block.use_fake_user:
                orphan_block_users_find = True
                bpy.data.libraries.remove(block)


def link_collection_to_collection(collection_to_link, collection):
    """link an item to a collection"""
    if collection_to_link not in collection.children.values():
        collection.children.link(collection_to_link)


def link_object_to_collection(object_to_link, collection):
    """link an item to a collection"""
    if object_to_link not in collection.objects.values():
        collection.objects.link(object_to_link)


def set_fake_user_on_orphans():
    """set fake user on orphans to avoid orphan purge"""
    properties = property_names.copy()
    items_with_fake_user_list = list()
    for prop in properties:
        data = getattr(bpy.data, prop)
        for block in data:
            if block.users == 0:
                try:
                    block.use_fake_user = True
                    items_with_fake_user_list.append(block)
                except Exception as e:
                    print("Set Fake User Failed", e)

    return items_with_fake_user_list


def remove_fake_user_on_orphans(items_with_fake_user_list):
    """remove fake user on orphans list to allow orphan purge"""
    for block in items_with_fake_user_list:
        try:
            block.use_fake_user = False
        except Exception as e:
            print("Remove Fake User Failed", e)


def model_asset_name(model_name: str, namespace: Optional[str] = None) -> str:
    """Return a consistent name for an asset."""
    name = f"{model_name}"
    if namespace:
        name = f"{name}_{namespace}"
    return name


def get_parent_collections(collection):
    """Return the parent collection of a collection"""
    collections = list()
    for parent_collection in bpy.data.collections:
        if collection in parent_collection.children.values():
            collections.append(parent_collection)
    return collections


def get_container_collections() -> list:
    """Return all 'model' collections.

    Check if the family is 'model' and if it doesn't have the
    representation set. If the representation is set, it is a loaded model
    and we don't want to publish it.
    """
    collections = []
    for collection in bpy.data.collections:
        if collection.get(AVALON_PROPERTY):
            collections.append(collection)
    return collections


def set_original_name_for_objects_container(container, has_namespace=False):
    # Set the orginal_name for all the objects and collections in the container
    # or namespace + original name if AVALON_TASK != "modelling"
    objects = get_all_objects_in_collection(container)
    for obj in objects:
        if obj.get("original_name"):
            if has_namespace and obj.get("namespace"):
                obj.name = (
                    f'{obj["namespace"]}:{obj["original_name"]}'
                )
            else:
                obj.name = obj["original_name"]
        if obj.data is not None:
            if obj.data.get("original_name"):
                if obj.type != "EMPTY":
                    if (
                        has_namespace
                        and obj.data.get("namespace")
                        and obj.data.get("original_name")
                    ):
                        obj.data.name = (
                            f'{obj.data["namespace"]}:'
                            f'{obj.data["original_name"]}'
                        )
                    else:
                        obj.data.name = obj.data["original_name"]

    collections = get_all_collections_in_collection(container)
    for collection in collections:
        if collection.get("original_name"):
            if has_namespace and collection.get("namespace"):
                collection.name = (
                    f'{collection["namespace"]}:{collection["original_name"]}'
                )
            else:
                collection.name = collection["original_name"]


def set_temp_namespace_for_objects_container(container):
    objects = get_all_objects_in_collection(container)
    for obj in objects:
        if obj.get("original_name"):
            obj.name = f'temp:{obj["original_name"]}'
        if obj.type != "EMPTY":
            if obj.data is not None:
                obj.data.name = f'temp:{obj["original_name"]}'
    collections = get_all_collections_in_collection(container)
    for collection in collections:
        if collection.get("original_name"):
            collection.name = f'temp:{collection["original_name"]}'


def remove_namespace_for_objects_container(container):
    objects = get_all_objects_in_collection(container)
    for obj in objects:
        name = obj.name
        name_split = name.split(":")
        if len(name_split) > 1:
            name = name_split[1]
        obj.name = name
    collections = get_all_collections_in_collection(container)
    for collection in collections:
        name = collection.name
        name_split = name.split(":")
        if len(name_split) > 1:
            name = name_split[1]
        collection.name = name


def get_containers_list():
    """Get all the containers"""
    instances = []
    nodes = bpy.data.collections

    for collection in nodes:
        if collection.get(AVALON_PROPERTY):
            instances.append(collection)
    return instances


def get_all_collections_in_collection(collection):
    """get_all_collections_in_collection"""
    check_list = collection.children.values()
    for c in check_list:
        check_list.extend(c.children)

    return check_list


def get_all_objects_in_collection(collection_input):
    """get all object names of the collection's object"""

    # Get the collections in the the collection_input
    collection_list = collection_input.children.values()
    collection_list.append(collection_input)
    objects_list = list()

    # Get all recursively the collections in the collectin_input
    for collection in collection_list:
        collection_list.extend(collection.children)

    # Get all recursively the objects in the collectin_input
    for collection in collection_list:
        nodes = collection.objects.values()
        for obj in nodes:
            if obj not in objects_list:
                objects_list.append(obj)
            nodes.extend(obj.children)
    return objects_list


def get_model_unique_number(current_container_name: str) -> str:
    """Return a unique number based on the asset name."""
    data_collections = bpy.data.collections
    container_names = [
        c.name for c in data_collections if c.get(AVALON_PROPERTY)
    ]
    if container_names:
        return "001"
    count = 1
    name = f"{current_container_name}_{count:0>3}"
    # increment the name as long as it's in container_names.
    # If it's not inside it's the right increment
    while name in container_names:
        count += 1
        name = f"{current_container_name}_{count:0>3}"
    return f"{count:0>3}"


def is_local_collection(collection):
    """Check if all members of a collection are local"""
    for obj in collection.all_objects:
        if obj.library is None and obj.override_library is None:
            return True
    collections_list = get_all_collections_in_collection(collection)
    # collections_list.append(collection)
    for collection in collections_list:
        if collection.library is None and collection.override_library is None:
            return True
    return False


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
