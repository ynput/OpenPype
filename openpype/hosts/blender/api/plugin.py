"""Shared functionality for pipeline plugins for Blender."""

from pathlib import Path
from typing import Dict, List, Optional

import bpy

from openpype.pipeline import (
    LegacyCreator,
    LoaderPlugin,
)
from .pipeline import AVALON_CONTAINERS
from .ops import (
    MainThreadItem,
    execute_in_main_thread
)
from .lib import (
    imprint,
    get_selection
)

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


def get_unique_number(
    asset: str, subset: str
) -> str:
    """Return a unique number based on the asset name."""
    avalon_container = bpy.data.collections.get(AVALON_CONTAINERS)
    if not avalon_container:
        return "01"
    asset_groups = avalon_container.all_objects

    container_names = [c.name for c in asset_groups if c.type == 'EMPTY']
    count = 1
    name = f"{asset}_{count:0>2}_{subset}"
    while name in container_names:
        count += 1
        name = f"{asset}_{count:0>2}_{subset}"
    return f"{count:0>2}"


def prepare_data(data, container_name=None):
    name = data.name
    local_data = data.make_local()
    if container_name:
        local_data.name = f"{container_name}:{name}"
    else:
        local_data.name = f"{name}"
    return local_data


def create_blender_context(active: Optional[bpy.types.Object] = None,
                           selected: Optional[bpy.types.Object] = None,):
    """Create a new Blender context. If an object is passed as
    parameter, it is set as selected and active.
    """

    if not isinstance(selected, list):
        selected = [selected]

    override_context = bpy.context.copy()

    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        override_context['window'] = win
                        override_context['screen'] = win.screen
                        override_context['area'] = area
                        override_context['region'] = region
                        override_context['scene'] = bpy.context.scene
                        override_context['active_object'] = active
                        override_context['selected_objects'] = selected
                        return override_context
    raise Exception("Could not create a custom Blender context.")


def get_parent_collection(collection):
    """Get the parent of the input collection"""
    check_list = [bpy.context.scene.collection]

    for c in check_list:
        if collection.name in c.children.keys():
            return c
        check_list.extend(c.children)

    return None


def get_local_collection_with_name(name):
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
        if obj.mode != 'OBJECT':
            modes.append((obj, obj.mode))
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='DESELECT')

    for p in modes:
        bpy.context.view_layer.objects.active = p[0]
        bpy.ops.object.mode_set(mode=p[1])

    bpy.context.view_layer.objects.active = active


class Creator(LegacyCreator):
    """Base class for Creator plug-ins."""
    defaults = ['Main']

    def process(self):
        collection = bpy.data.collections.new(name=self.data["subset"])
        bpy.context.scene.collection.children.link(collection)
        imprint(collection, self.data)

        if (self.options or {}).get("useSelection"):
            for obj in get_selection():
                collection.objects.link(obj)

        return collection


class Loader(LoaderPlugin):
    """Base class for Loader plug-ins."""

    hosts = ["blender"]


class AssetLoader(LoaderPlugin):
    """A basic AssetLoader for Blender

    This will implement the basic logic for linking/appending assets
    into another Blender scene.

    The `update` method should be implemented by a sub-class, because
    it's different for different types (e.g. model, rig, animation,
    etc.).
    """

    @staticmethod
    def _get_instance_empty(instance_name: str, nodes: List) -> Optional[bpy.types.Object]:
        """Get the 'instance empty' that holds the collection instance."""
        for node in nodes:
            if not isinstance(node, bpy.types.Object):
                continue
            if (node.type == 'EMPTY' and node.instance_type == 'COLLECTION'
                    and node.instance_collection and node.name == instance_name):
                return node
        return None

    @staticmethod
    def _get_instance_collection(instance_name: str, nodes: List) -> Optional[bpy.types.Collection]:
        """Get the 'instance collection' (container) for this asset."""
        for node in nodes:
            if not isinstance(node, bpy.types.Collection):
                continue
            if node.name == instance_name:
                return node
        return None

    @staticmethod
    def _get_library_from_container(container: bpy.types.Collection) -> bpy.types.Library:
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

        assert len(
            libraries) == 1, "'{container.name}' contains objects from more then 1 library."

        return list(libraries)[0]

    def process_asset(self,
                      context: dict,
                      name: str,
                      namespace: Optional[str] = None,
                      options: Optional[Dict] = None):
        """Must be implemented by a sub-class"""
        raise NotImplementedError("Must be implemented by a sub-class")

    def load(self,
             context: dict,
             name: Optional[str] = None,
             namespace: Optional[str] = None,
             options: Optional[Dict] = None) -> Optional[bpy.types.Collection]:
        """ Run the loader on Blender main thread"""
        mti = MainThreadItem(self._load, context, name, namespace, options)
        execute_in_main_thread(mti)

    def _load(self,
              context: dict,
              name: Optional[str] = None,
              namespace: Optional[str] = None,
              options: Optional[Dict] = None
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
        unique_number = get_unique_number(
            asset, subset
        )
        namespace = namespace or f"{asset}_{unique_number}"
        name = name or asset_name(
            asset, subset, unique_number
        )

        nodes = self.process_asset(
            context=context,
            name=name,
            namespace=namespace,
            options=options,
        )

        # Only containerise if anything was loaded by the Loader.
        if not nodes:
            return None

        # Only containerise if it's not already a collection from a .blend file.
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
        """ Run the update on Blender main thread"""
        mti = MainThreadItem(self.exec_update, container, representation)
        execute_in_main_thread(mti)

    def exec_remove(self, container: Dict) -> bool:
        """Must be implemented by a sub-class"""
        raise NotImplementedError("Must be implemented by a sub-class")

    def remove(self, container: Dict) -> bool:
        """ Run the remove on Blender main thread"""
        mti = MainThreadItem(self.exec_remove, container)
        execute_in_main_thread(mti)
