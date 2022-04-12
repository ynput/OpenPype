"""Shared functionality for pipeline plugins for Blender."""

from pathlib import Path
from typing import Dict, List, Optional, Generator

import bpy

import avalon.api
from openpype.api import PypeCreatorMixin
from .pipeline import AVALON_PROPERTY
from .ops import MainThreadItem, execute_in_main_thread
from .lib import imprint, get_selection
from openpype.hosts.blender.api import plugin

VALID_EXTENSIONS = [".blend", ".json", ".abc", ".fbx"]


def asset_name(
    asset: str, subset: str, namespace: Optional[str] = None
) -> str:
    """Return a consistent name for an asset."""
    name = f"{asset}"
    if namespace:
        name = f"{name}_{namespace}"
    name = f"{name}_{subset}"
    return name


def remove_container(container):
    items_with_fake_user_list = set_fake_user_on_orphans()
    objects = get_all_objects_in_collection(container)
    for object in objects:
        bpy.data.objects.remove(object)

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
        properties = [
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

        for property in properties:
            data = getattr(bpy.data, property)
            for block in data:
                if block.users == 0 and not block.use_fake_user:
                    orphan_block_users_find = True
                    data.remove(block)

        for block in bpy.data.libraries:
            if not block.users_id and not block.use_fake_user:
                orphan_block_users_find = True
                bpy.data.libraries.remove(block)


def set_fake_user_on_orphans():
    """set fake user on orphans to avoid orphan purge"""
    properties = [
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
    items_with_fake_user_list = list()
    for property in properties:
        data = getattr(bpy.data, property)
        for block in data:
            if block.users == 0:
                block.use_fake_user = True
                items_with_fake_user_list.append(block)
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


def get_unique_number(asset: str, subset: str) -> str:
    """Return a unique number based on the asset name."""
    data_collections = bpy.data.collections
    container_names = [
        c.name for c in data_collections if c.get(AVALON_PROPERTY)
    ]
    if container_names:
        return "01"
    count = 1
    name = f"{asset}_{count:0>2}_{subset}"
    while name in container_names:
        count += 1
        name = f"{asset}_{count:0>2}_{subset}"
    return f"{count:0>2}"


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
    while name in container_names:
        count += 1
        name = f"{current_container_name}_{count:0>3}"
    return f"{count:0>3}"


def prepare_data(data, container_name=None):
    name = data.name
    name_split = name.split(":")
    if len(name_split) > 1:
        name = name_split[1]
    if container_name:
        data.name = f"{container_name}:{name}"
    else:
        data.name = f"{name}"

    return data.name


def set_original_name_for_objects_container(container, has_namespace=False):
    # Set the orginal_name for all the objects and collections in the container
    # or namespace + original name if AVALON_TASK != "modelling"
    objects = plugin.get_all_objects_in_collection(container)
    for object in objects:
        if object.get("original_name"):
            if has_namespace and object.get("namespace"):
                object.name = (
                    f'{object["namespace"]}:{object["original_name"]}'
                )
            else:
                object.name = object["original_name"]

        if object.data.get("original_name"):
            if object.type != "EMPTY":
                if (
                    has_namespace
                    and object.data.get("namespace")
                    and object.data.get("original_name")
                ):
                    object.data.name = (
                        f'{object.data["namespace"]}:'
                        f'{object.data["original_name"]}'
                    )
                else:
                    object.data.name = object.data["original_name"]

    collections = plugin.get_all_collections_in_collection(container)
    for collection in collections:
        if collection.get("original_name"):
            if has_namespace and collection.get("namespace"):
                collection.name = (
                    f'{collection["namespace"]}:{collection["original_name"]}'
                )
            else:
                collection.name = collection["original_name"]


def set_temp_namespace_for_objects_container(container):
    objects = plugin.get_all_objects_in_collection(container)
    for object in objects:
        if object.get("original_name"):
            object.name = f'temp:{object["original_name"]}'
        if object.type != "EMPTY":
            object.data.name = f'temp:{object["original_name"]}'
    collections = plugin.get_all_collections_in_collection(container)
    for collection in collections:
        if collection.get("original_name"):
            collection.name = f'temp:{collection["original_name"]}'


def remove_namespace_for_objects_container(container):
    objects = plugin.get_all_objects_in_collection(container)
    for object in objects:
        name = object.name
        name_split = name.split(":")
        if len(name_split) > 1:
            name = name_split[1]
        object.name = name
    collections = plugin.get_all_collections_in_collection(container)
    for collection in collections:
        name = collection.name
        name_split = name.split(":")
        if len(name_split) > 1:
            name = name_split[1]
        collection.name = name


def create_blender_context(
    active: Optional[bpy.types.Object] = None,
    selected: Optional[bpy.types.Object] = None,
):
    """Create a new Blender context. If an object is passed as
    parameter, it is set as selected and active.
    """

    if not isinstance(selected, list):
        selected = [selected]

    override_context = bpy.context.copy()

    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "WINDOW":
                        override_context["window"] = win
                        override_context["screen"] = win.screen
                        override_context["area"] = area
                        override_context["region"] = region
                        override_context["scene"] = bpy.context.scene
                        override_context["active_object"] = active
                        override_context["selected_objects"] = selected
                        return override_context
    raise Exception("Could not create a custom Blender context.")


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
        for object in nodes:
            if object not in objects_list:
                objects_list.append(object)
            nodes.extend(object.children)
    return objects_list


def get_parent_collection(collection):
    """Get the parent of the input collection"""
    check_list = [bpy.context.scene.collection]
    for c in check_list:
        if collection.name in c.children.keys():
            return c
        check_list.extend(c.children)
    return None


def is_local_collection(collection):
    """Check if all members of a collection are local"""
    for object in collection.all_objects:
        if object.library is None and object.override_library is None:
            return True
    collections_list = get_all_collections_in_collection(collection)
    # collections_list.append(collection)
    for collection in collections_list:
        if collection.library is None and collection.override_library is None:
            return True
    return False


def get_local_collection_with_name(name):
    """Get collection without library"""
    for collection in bpy.data.collections:
        if collection.name == name and collection.library is None:
            return collection
    return None


def deselect_all():
    """Deselect all objects in the scene.

    Blender gives context error if trying to deselect object that it isn't
    in object mode.
    """
    modes = []
    active = bpy.context.view_layer.objects.active

    for obj in bpy.data.objects:
        if obj.mode != "OBJECT":
            modes.append((obj, obj.mode))
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.object.select_all(action="DESELECT")

    for p in modes:
        bpy.context.view_layer.objects.active = p[0]
        bpy.ops.object.mode_set(mode=p[1])

    bpy.context.view_layer.objects.active = active


class Creator(PypeCreatorMixin, avalon.api.Creator):
    """Base class for Creator plug-ins."""

    def process(self):
        collection = bpy.data.collections.new(name=self.data["subset"])
        bpy.context.scene.collection.children.link(collection)
        imprint(collection, self.data)

        if (self.options or {}).get("useSelection"):
            for obj in get_selection():
                collection.objects.link(obj)

        return collection


class Loader(avalon.api.Loader):
    """Base class for Loader plug-ins."""

    hosts = ["blender"]


class AssetLoader(avalon.api.Loader):
    """A basic AssetLoader for Blender

    This will implement the basic logic for linking/appending assets
    into another Blender scene.

    The `update` method should be implemented by a sub-class, because
    it's different for different types (e.g. model, rig, animation,
    etc.).
    """

    @staticmethod
    def _get_instance_empty(
        instance_name: str, nodes: List
    ) -> Optional[bpy.types.Object]:
        """Get the 'instance empty' that holds the collection instance."""
        for node in nodes:
            if not isinstance(node, bpy.types.Object):
                continue
            if (
                node.type == "EMPTY"
                and node.instance_type == "COLLECTION"
                and node.instance_collection
                and node.name == instance_name
            ):
                return node
        return None

    @staticmethod
    def _get_instance_collection(
        instance_name: str, nodes: List
    ) -> Optional[bpy.types.Collection]:
        """Get the 'instance collection' (container) for this asset."""
        for node in nodes:
            if not isinstance(node, bpy.types.Collection):
                continue
            if node.name == instance_name:
                return node
        return None

    @staticmethod
    def _get_library_from_container(
        container: bpy.types.Collection,
    ) -> bpy.types.Library:
        """Find the library file from the container.

        It traverses the objects from this collection, checks if there is only
        1 library from which the objects come from and returns the library.

        Warning:
            No nested collections are supported at the moment!
        """
        assert not container.children, "Nested collections are not supported."
        assert container.objects, "The collection doesn't contain any objects."
        libraries = set()
        for obj in container.objects:
            assert obj.library, f"'{obj.name}' is not linked."
            libraries.add(obj.library)

        assert (
            len(libraries) == 1
        ), "'{container.name}' contains objects from more then 1 library."

        return list(libraries)[0]

    def process_asset(
        self,
        context: dict,
        name: str,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None,
    ):
        """Must be implemented by a sub-class"""
        raise NotImplementedError("Must be implemented by a sub-class")

    def load(
        self,
        context: dict,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None,
    ) -> Optional[bpy.types.Collection]:
        """Run the loader on Blender main thread"""
        mti = MainThreadItem(self._load, context, name, namespace, options)
        execute_in_main_thread(mti)

    def _load(
        self,
        context: dict,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None,
    ) -> Optional[bpy.types.Collection]:
        """Load asset via database

        Arguments:
            context: Full parenthood of representation to load
            name: Use pre-defined name
            namespace: Use pre-defined namespace
            options: Additional settings dictionary
        """
        # TODO (jasper): make it possible to add the asset several times by
        # just re-using the collection
        assert Path(self.fname).exists(), f"{self.fname} doesn't exist."

        asset = context["asset"]["name"]
        subset = context["subset"]["name"]
        unique_number = get_unique_number(asset, subset)
        namespace = namespace or f"{asset}_{unique_number}"
        name = name or asset_name(asset, subset, unique_number)

        nodes = self.process_asset(
            context=context,
            name=name,
            namespace=namespace,
            options=options,
        )

        # Only containerise if anything was loaded by the Loader.
        if not nodes:
            return None

        # Only containerise if it's not already a collection
        # from a .blend file.
        # representation = context["representation"]["name"]
        # if representation != "blend":
        #     from avalon.blender.pipeline import containerise
        #     return containerise(
        #         name=name,
        #         namespace=namespace,
        #         nodes=nodes,
        #         context=context,
        #         loader=self.__class__.__name__,
        #     )

        # asset = context["asset"]["name"]
        # subset = context["subset"]["name"]
        # instance_name = asset_name(asset, subset, unique_number) + '_CON'

        # return self._get_instance_collection(instance_name, nodes)

    def exec_update(self, container: Dict, representation: Dict):
        """Must be implemented by a sub-class"""
        raise NotImplementedError("Must be implemented by a sub-class")

    def update(self, container: Dict, representation: Dict):
        """Run the update on Blender main thread"""
        mti = MainThreadItem(self.exec_update, container, representation)
        execute_in_main_thread(mti)

    def exec_remove(self, container: Dict) -> bool:
        """Must be implemented by a sub-class"""
        raise NotImplementedError("Must be implemented by a sub-class")

    def remove(self, container: Dict) -> bool:
        """Run the remove on Blender main thread"""
        mti = MainThreadItem(self.exec_remove, container)
        execute_in_main_thread(mti)
