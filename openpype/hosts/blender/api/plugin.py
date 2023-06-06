"""Shared functionality for pipeline plugins for Blender."""

from pathlib import Path
from typing import Dict, List, Optional

import bpy

from openpype.pipeline import (
    Creator,
    CreatedInstance,
    LoaderPlugin,
)
from .pipeline import (
    AVALON_CONTAINERS,
    AVALON_INSTANCES,
    AVALON_PROPERTY,
)
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
                           selected: Optional[bpy.types.Object] = None,
                           window: Optional[bpy.types.Window] = None):
    """Create a new Blender context. If an object is passed as
    parameter, it is set as selected and active.
    """

    if not isinstance(selected, list):
        selected = [selected]

    override_context = bpy.context.copy()

    windows = [window] if window else bpy.context.window_manager.windows

    for win in windows:
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


class BlenderCreator(Creator):
    """Base class for Blender Creator plug-ins."""
    defaults = ['Main']

    # Deprecated?
    def process(self):
        collection = bpy.data.collections.new(name=self.data["subset"])
        bpy.context.scene.collection.children.link(collection)
        imprint(collection, self.data)

        if (self.options or {}).get("useSelection"):
            for obj in get_selection():
                collection.objects.link(obj)

        return collection


    @staticmethod
    def cache_subsets(shared_data):
        """Cache instances for Creators shared data.

        Create `blender_cached_subsets` key when needed in shared data and
        fill it with all collected instances from the scene under its
        respective creator identifiers.

        If legacy instances are detected in the scene, create
        `blender_cached_legacy_subsets` key and fill it with
        all legacy subsets from this family as a value.  # key or value?

        Args:
            shared_data(Dict[str, Any]): Shared data.

        Return:
            Dict[str, Any]: Shared data with cached subsets.
        """
        if not shared_data.get('blender_cached_subsets'):
            cache = {}
            cache_legacy = {}

            avalon_instances = bpy.data.collections.get(AVALON_INSTANCES)
            if avalon_instances:
                for obj in bpy.data.collections.get(AVALON_INSTANCES).objects:
                    avalon_prop = obj.get(AVALON_PROPERTY, {})
                    if avalon_prop.get('id') == 'pyblish.avalon.instance':
                        creator_id = avalon_prop.get('creator_identifier')

                        if creator_id:
                            # Creator instance
                            cache.setdefault(creator_id, []).append(
                                avalon_prop
                            )
                        else:
                            family = avalon_prop.get('family')
                            if family:
                                # Legacy creator instance
                                cache_legacy.setdefault(family, []).append(
                                    avalon_prop
                                )

            for col in bpy.data.collections:
                avalon_prop = col.get(AVALON_PROPERTY, {})
                if avalon_prop.get('id') == 'pyblish.avalon.instance':
                    creaor_id = avalon_prop.get('creator_identifier')

                    if creator_id:
                        # Creator instance
                        cache.setdefault(creator_id, []).append(avalon_prop)
                    else:
                        family = avalon_prop.get('family')
                        if family:
                            cache_legacy.setdefault(family, [])
                            if family:
                                # Legacy creator instance
                                cache_legacy.setdefault(family, []).append(
                                    avalon_prop
                                )


    def create(
        self, subset_name: str, instance_data: dict, pre_create_data: dict
    ):
        """Override abstract method from Creator.
        Create new instance and store it.

        Args:
            subset_name(str): Subset name of created instance.
            instance_data(dict): Base data for instance.
            pre_create_data(dict): Data based on pre creation attributes.
                Those may affect how creator works.
        """
        instance = CreatedInstance(
            self.family, subset_name, instance_data
        )

        collection = bpy.data.collections.new(name=self.data['subset'])
        bpy.context.scene.collection.children.link(collection)

        if (self.options or {}).get("useSelection"):
            for obj in get_selection():
                collection.objects.link(obj)


    def collect_instances(self):
        """Override abstract method from BaseCreator.
        Collect existing instances related to this creator plugin."""

        # Cache subsets in shared data
        self.cache_subsets(self.collection_shared_data)

        # Get cached subsets
        cached_subsets = self.collection_shared_data.get('blender_cached_subsets')
        if not cached_subsets:
            return

        for instance_data in cached_subsets:
            # Process only instances that were created by this creator
            creator_id = instance_data.get('creator_identifier')

            if creator_id == self.identifier:
                # Create instance object from existing data
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )

                # Add instance to create context
                self.add_instance_to_context(instance)


    def update_instances(self, update_list):
        """Override abstract method from BaseCreator.
        Store changes of existing instances so they can be recollected.

        Args:
            update_list(List[UpdateData]): Changed instances
                and their changes, as a list of tuples."""
        for created_instance, _changes in update_list:
            data = created_instance.data_to_store()

            # TODO


    def remove_instances(self, instances: List[CreatedInstance]):
        """Override abstract method from BaseCreator.
        Method called when instances are removed.

        Args:
            instance(List[CreatedInstance]): Instance objects to remove.
        """
        for instance in instances:
            self._remove_instance_from_context(instance)


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
        filepath = self.filepath_from_context(context)
        assert Path(filepath).exists(), f"{filepath} doesn't exist."

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
        #     from openpype.hosts.blender.api.pipeline import containerise
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
