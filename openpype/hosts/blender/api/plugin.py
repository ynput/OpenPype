"""Shared functionality for pipeline plugins for Blender."""

from pprint import pformat
from inspect import getmembers
from pathlib import Path
from string import digits
import threading
from typing import Callable, Dict, List, Optional, Set, Tuple, Union, Iterator
from bson.objectid import ObjectId

import bpy
from mathutils import Matrix

from openpype.api import Logger
from openpype.hosts.blender.api.properties import (
    OpenpypeContainer,
    OpenpypeInstance,
)
from openpype.hosts.blender.api.utils import (
    BL_OUTLINER_TYPES,
    BL_TYPE_DATAPATH,
    BL_TYPE_ICON,
    get_children_recursive,
    get_parent_collection,
    link_to_collection,
    unlink_from_collection,
)
from openpype.pipeline import (
    legacy_io,
    LegacyCreator,
    LoaderPlugin,
    get_representation_path,
    AVALON_CONTAINER_ID,
)
from .ops import (
    MainThreadItem,
    execute_in_main_thread
)
from .lib import (
    add_datablocks_to_container,
    create_container,
    imprint,
    get_selection
)
from .pipeline import metadata_update, AVALON_PROPERTY


VALID_EXTENSIONS = [".blend", ".json", ".abc", ".fbx"]

log = Logger.get_logger(__name__)


def build_op_basename(
    asset: str, subset: str, namespace: Optional[str] = None
) -> str:
    """Return a consistent name for an asset."""
    name = f"{asset}"
    if namespace:
        name = f"{name}_{namespace}"
    name = f"{name}_{subset}"
    return name


def get_unique_number(
    asset: str, subset: str, start_number: Optional[int] = None
) -> str:
    """Return a unique number based on the asset name."""
    container_names = [c.name for c in bpy.data.collections]
    container_names += [
        obj.name
        for obj in bpy.data.objects
        if obj.instance_collection and obj.instance_type == 'COLLECTION'
    ]
    count = start_number or 1
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


def context_override(
    active: Optional[bpy.types.Object] = None,
    selected: Optional[bpy.types.Object] = None,
    window: Optional[bpy.types.Window] = None,
    area_type: Optional[str] = "VIEW_3D"
):
    """Create a new Blender context. If an object is passed as
    parameter, it is set as selected and active.
    """

    if not isinstance(selected, list):
        selected = [selected]

    windows = [window] if window else bpy.context.window_manager.windows

    for win in windows:
        for area in win.screen.areas:
            if area.type == area_type:
                for region in area.regions:
                    if region.type == "WINDOW":
                        return bpy.context.temp_override(
                            window=win,
                            area=area,
                            region=region,
                            active_object=active,
                            selected_objects=selected,
                        )
    raise Exception("Could not create a custom Blender context.")


def remove_container_datablocks(container: OpenpypeContainer):
    """Remove datablocks referenced in container.

    Datablocks are removed from the blend file first,
    then dereferenced from the container.

    Args:
        container (OpenpypeContainer): Container to remove datablocks of.
    """
    for d_ref in container.datablock_refs:
        if d_ref.datablock:
            datapath = getattr(
                bpy.data, BL_TYPE_DATAPATH.get(type(d_ref.datablock))
            )
            d_ref.datablock.use_fake_user = False
            datapath.remove(d_ref.datablock)

    container.datablock_refs.clear()


def remove_container(
    container: Union[bpy.types.Collection, bpy.types.Object]
):
    """Remove the container with all its datablocks.

    Arguments:
        container: The collection or empty container to be removed.

    Note: TODO
        This rename all removed elements with .removed suffix to prevent
        naming conflict with created object before calling orphans_purge.
    """
    remove_container_datablocks(container)

    # Delete library
    if container.library and len(container.library.users_id) == 0:
        bpy.data.libraries.remove(container.library)

    # Delete container
    openpype_containers = bpy.context.scene.openpype_containers
    openpype_containers.remove(openpype_containers.find(container.name))

    # Orphan purge
    orphans_purge()


def is_container(entity, family: Optional[str] = None) -> bool:
    """Check if given entity is a valid container.

    Arguments:
        entity: The entity to check.
        family: If is set and entity is container, this family must match
            with the given family name.

    Returns:
        Return true if entity is a valid container.
    """
    if (
        isinstance(entity, (bpy.types.Collection, bpy.types.Object))
        and entity.get(AVALON_PROPERTY)
        and entity[AVALON_PROPERTY].get("id") == AVALON_CONTAINER_ID
    ):
        if not family or entity[AVALON_PROPERTY].get("family") == family:
            return True
    return False


def is_container_up_to_date(
    container: Union[bpy.types.Collection, bpy.types.Object]
) -> bool:
    """Check if container is up to date.

    Arguments:
        container: The container to check.

    Returns:
        Return true if container is up to date.
    """

    metadata = container.get(AVALON_PROPERTY, {})

    if (
        isinstance(container, bpy.types.Object)
        and container.is_instancer
        and container.instance_collection
    ):
        metadata.update(
            container.instance_collection.get(AVALON_PROPERTY, {})
        )

    current_representation_id = metadata.get("representation", "")
    last_representation = get_last_representation(current_representation_id)
    last_libpath = get_representation_path(last_representation)

    current_libpath = metadata.get("libpath", "")

    current_libpath = Path(bpy.path.abspath(current_libpath)).resolve()
    last_libpath = Path(bpy.path.abspath(last_libpath)).resolve()

    return current_libpath == last_libpath


def get_last_representation(representation_id: str) -> Optional[Dict]:
    """Get last representation of the given representation id.

    Arguments:
        representation_id: The representation id.

    Returns:
        The last representation dict or None if not found.
    """
    current_representation = legacy_io.find_one({
        "_id": ObjectId(representation_id)
    })
    current_version, subset, asset, project = legacy_io.parenthood(
        current_representation
    )
    last_version = legacy_io.find_one(
        {"type": "version", "parent": subset["_id"]},
        sort=[("name", -1)]
    )
    last_representation = legacy_io.find_one({
        "type": "representation",
        "parent": last_version["_id"],
        "name": current_representation["name"]
    })

    return last_representation


def get_container_objects(
    container: Union[bpy.types.Collection, bpy.types.Object]
) -> List[bpy.types.Object]:
    """Get recursively all the child objects for the given container collection
    or object empty.

    Arguments:
        container: The parent container.

    Returns:
        All the child objects of the container.
    """
    return [
        d_ref.datablock
        for d_ref in container.datablock_refs
        if type(d_ref.datablock) is bpy.types.Object
        and d_ref.datablock != container.outliner_entity
    ]


def get_collections_by_objects(
    objects: List[bpy.types.Object],
    collections: Optional[List[bpy.types.Collection]] = None
) -> Iterator[bpy.types.Collection]:
    """Get collections who contain the compete given list of objects from all
    scene collections or given list of collections.

    Arguments:
        objects: The list of objects who need to be contained in the
            returned collections.
        collections: The list of collections used to get requested
            collections. If not defined, we use all the childrens from
            scene collection.

    Yields:
        The next requested collection.
    """
    if collections is None:
        collections = list(bpy.context.scene.collection.children)
    for collection in collections:
        if not len(collection.all_objects):
            continue
        elif all([obj in objects for obj in collection.all_objects]):
            yield collection
        elif len(collection.children):
            yield from get_collections_by_objects(objects, collection.children)


def get_collections_by_armature(
    armature: bpy.types.Object,
    collections: Optional[List[bpy.types.Collection]] = None
) -> Iterator[bpy.types.Collection]:
    """Get collections who contain the given armature from all
    scene collections or given list of collections.

    Arguments:
        armature: The armature who need to be contained in the
            returned collections.
        collections: The list of collections used to get requested
            collections. If not defined, we use all the childrens from
            scene collection.

    Yields:
        The next requested collection.
    """
    if collections is None:
        collections = list(bpy.context.scene.collection.children)
    for collection in collections:
        if armature in list(collection.objects):
            yield collection
        elif len(collection.children):
            yield from get_collections_by_armature(
                armature, collection.children
            )


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


def orphans_purge():
    """Purge orphan datablocks and libraries."""
    # clear unused datablock
    bpy.data.orphans_purge(do_recursive=False)

    # clear unused libraries
    for library in list(bpy.data.libraries):
        if len(library.users_id) == 0:
            bpy.data.libraries.remove(library)


def make_local(obj, data_local=True):
    """Make local for the given linked object."""
    if obj.override_library:
        # NOTE : obj.make_local() don't do the job.
        # obj.make_local(clear_proxy=True) is deprecated and don't
        # work with override_library.
        # And obj.override_library.destroy() with obj.make_local() we lost
        # all the overrided properties.
        obj_name = obj.name
        deselect_all()
        obj.select_set(True)
        with context_override(active=obj, selected=obj):
            bpy.ops.object.make_local(
                type="SELECT_OBDATA" if data_local else "SELECT_OBJECT",
            )
        obj = bpy.context.scene.objects.get(obj_name)
    elif obj.library:
        obj = obj.make_local()
        if data_local:
            obj.data.make_local()
    return obj

def exec_process(process_func: Callable):
    """Decorator to make sure the process function is executed in main thread.

    OP GUI is not run in Blender's thread to avoid disruptions.

    Args:
        func (Callable): Process function to execute.
    """
    def wrapper_exec_process(*args, **kwargs):
        if threading.current_thread() is not threading.main_thread():
            mti = MainThreadItem(process_func, *args, **kwargs)
            execute_in_main_thread(mti)
            return mti
        else:
            return process_func(*args, **kwargs)
    return wrapper_exec_process


class Creator(LegacyCreator):
    """Base class for Creator plug-ins."""
    defaults = ['Main']
    color_tag = "COLOR_07"
    bl_types = BL_OUTLINER_TYPES

    @staticmethod
    def _filter_outliner_datablocks(
        datablocks: List,
    ) -> Tuple[Set[bpy.types.Collection], Set[bpy.types.Object]]:
        collections = set()
        objects = set()
        for block in datablocks:
            # Collections
            if type(block) is bpy.types.Collection:
                collections.add(block)
            # Objects
            elif type(block) is bpy.types.Object:
                objects.add(block)
        return collections, objects

    def _link_to_container_collection(
        self,
        container_collection: bpy.types.Collection,
        collections: List[bpy.types.Collection],
        objects: List[bpy.types.Object],
    ):
        """Link objects and then collections to the container collection.

        Args:
            container_collection (bpy.types.Collection): Container collection
                to link to.
            collections (List[bpy.types.Collection]): Collections to link.
            objects (List[bpy.types.Object]): Objects to link.
        """
        # Link Selected
        link_to_collection(objects, container_collection)
        link_to_collection(collections, container_collection)

        # Unlink from scene collection root if needed
        for obj in objects:
            if obj in set(bpy.context.scene.collection.objects):
                bpy.context.scene.collection.objects.unlink(obj)
        for collection in collections:
            if collection in set(bpy.context.scene.collection.children):
                bpy.context.scene.collection.children.unlink(collection)

    def _process_outliner(
        self, datablocks: List[bpy.types.ID], collection_name: str
    ) -> bpy.types.Collection:
        """Process outliner structure in case it concerns outliner datablocks.

        Link all objects and collections to a single container collection with
            appropriate name.
        In case there is only one collection between the container one and the
            objects, it's removed.

        Args:
            datablocks (List[bpy.types.ID]): Datablocks to filter and link to
                container collection
            collection_name (str): Name of the container collection

        Returns:
            bpy.types.Collection: Created container collection
        """
        # Filter outliner datablocks
        collections, objects = self._filter_outliner_datablocks(datablocks)

        # Determine collections to include if all children are included
        for collection in get_collections_by_objects(objects):
            collections.add(collection)

            # Remove objects to not link them to container
            objects -= set(collection.all_objects)

        container_collection = bpy.data.collections.get(collection_name)
        if container_collection is None:
            # If only one collection handling all objects, use it as container
            collections_as_list = list(collections)
            if len(collections) == 1 and objects.issubset(
                set(collections_as_list[0].objects)
            ) and not collections_as_list[0].is_openpype_instance:
                container_collection = collections_as_list[0]
                container_collection.name = collection_name  # Rename
                collections.clear()  # Remove it from collections to link
            else:
                container_collection = bpy.data.collections.new(
                    collection_name
                )
                bpy.context.scene.collection.children.link(
                    container_collection
                )
            container_collection.is_openpype_instance = True

        # Set color tag
        if self.color_tag and hasattr(container_collection, "color_tag"):
            container_collection.color_tag = self.color_tag

        # Link datablocks to container
        self._link_to_container_collection(
            container_collection, collections, objects
        )

        return container_collection

    @exec_process
    def process(
        self, datablocks: List[bpy.types.ID] = None, gather_into_collection = True
    ) -> OpenpypeInstance:
        """Create openpype publishable instance from datablocks.

        Instances are created in `scene.openpype_instances`.
        If no datablocks are provided, it creates an empty instance.
        Processing datablocks for an instance which already exists
            appends the datablocks to it.

        Args:
            datablocks (List[bpy.types.ID], optional): Datablocks to process and append to instance. Defaults to None.
            gather_into_collection (bool): 
                Process outliner gathering of elements under a single collection.
                Defaults to True.

        Raises:
            RuntimeError: The instance already exists but no datablocks
                are provided.

        Returns:
            OpenpypeInstance: Created or existing instance
        """

        # Get info from data and create name value.
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = build_op_basename(asset, subset)

        # Use selected objects if useSelection is True
        if (self.options or {}).get("useSelection"):
            # Get collection from selected objects
            datablocks = get_selection()
        else:
            datablocks = datablocks or []

        # Create the container
        op_instance = bpy.context.scene.openpype_instances.get(name)
        if op_instance is None:
            op_instance = bpy.context.scene.openpype_instances.add()
            op_instance.name = name

            # Keep types matches
            op_instance["icons"] = [
                BL_TYPE_ICON.get(t, "NONE") for t in self.bl_types
            ]
            op_instance["creator_name"] = self.__class__.__name__
        else:
            # If no datablocks, then empty instance is already existing
            if not datablocks:
                raise RuntimeError(f"This instance already exists: {name}")

        # Add custom property on the instance container with the data.
        self.data["task"] = legacy_io.Session.get("AVALON_TASK")
        imprint(op_instance, self.data)

        # Process outliner if current creator relates to this types
        if gather_into_collection and bpy.types.Collection in self.bl_types:
            container_collection = self._process_outliner(datablocks, name)
            imprint(container_collection, self.data)

            # Substitute collection to datablocks
            datablocks = [container_collection]

        # Add datablocks to openpype instance
        for d in datablocks:
            # Skip if already existing
            if op_instance.datablock_refs.get(d.name):
                continue

            instance_datablock = op_instance.datablock_refs.add()
            instance_datablock.datablock = d

            # Make datablock with fake user
            instance_datablock.keep_fake_user = d.use_fake_user
            d.use_fake_user = True

        return op_instance

    def _remove_instance(self, instance_name: str) -> bool:
        """Remove a created instance from a Blender scene.

        Arguments:
            instance_name: Name of instance to remove.

        Returns:
            Whether the instance was deleted.
        """
        # Get openpype instance
        openpype_instances = bpy.context.scene.openpype_instances
        op_instance_index = openpype_instances.find(instance_name)

        # Clear outliner if outliner data
        instance_collection = bpy.data.collections.get(instance_name)
        if instance_collection:
            parent_collection = get_parent_collection(instance_collection)

            # Move all children collections and objects to parent collection
            link_to_collection(
                list(instance_collection.objects)
                + list(instance_collection.children),
                parent_collection,
            )

            # Remove collection
            bpy.data.collections.remove(
                bpy.data.collections.get(instance_name)
            )

        # Remove fake user to datablocks
        op_instance = openpype_instances[op_instance_index]
        for d_ref in op_instance.datablock_refs:
            if d_ref.datablock:
                d_ref.datablock.use_fake_user = d_ref.keep_fake_user

        # Remove openpype instance
        openpype_instances.remove(op_instance_index)

        return True

class Loader(LoaderPlugin):
    """Base class for Loader plug-ins."""

    hosts = ["blender"]
    representations = []


class AssetLoader(Loader):
    """A basic AssetLoader for Blender

    This will implement the basic logic for linking/appending assets
    into another Blender scene.

    The `update` method should be implemented by a sub-class, because
    it's different for different types (e.g. model, rig, animation,
    etc.).
    """

    load_type = None

    # Default is outliner datablocks because it is the most common use case
    bl_types = BL_OUTLINER_TYPES

    color_tag = "COLOR_08"

    def _get_container_collection_from_collections(
        self,
        collections: List,
        container_name: str,
        famillies: Optional[List] = None,
    ) -> Optional[bpy.types.Collection]:
        """Get valid container from loaded collections.

        Args:
            collections (List): List of collections to find container in.
            container_name (str): Name of container to match.
            famillies (Optional[List], optional): Container family.
                Defaults to None.

        Returns:
            Optional[bpy.types.Collection]: Container collection.
        """
        return next(
            (col for col in collections if col.name == container_name), None
        )

    def _get_scene_container(
        self, container: dict
    ) -> Optional[OpenpypeContainer]:
        """Get container from current scene.

        Args:
            container (dict): Dict with container information.

        Returns:
            Optional[OpenpypeContainer]: Scene container. Can be None.
        """
        return bpy.context.scene.openpype_containers.get(
            container["objectName"]
        )

    def _load_library_datablocks(
        self,
        libpath: Path,
        container_name: str,
        container: OpenpypeContainer = None,
        link: Optional[bool] = True,
        do_override: Optional[bool] = False,
    ) -> Tuple[OpenpypeContainer, Set[bpy.types.ID]]:
        """Load datablocks from blend file library.

        Args:
            libpath (Path): Path of library.
            container_name (str): Name of container to be loaded.
            container (OpenpypeContainer): Load into existing container.
                Defaults to None.
            link (bool, optional): Only link datablocks (not made local).
                Defaults to True.
            do_override (bool, optional): Apply library override to
                linked datablocks. Defaults to False.

        Returns:
            Tuple[OpenpypeContainer, Set[bpy.types.ID]]: 
                (Created scene container, Loaded datablocks)
        """
        # Load datablocks from libpath library.
        loaded_data_collections = set()
        with bpy.data.libraries.load(
            libpath.as_posix(), link=link, relative=False
        ) as (
            data_from,
            data_to,
        ):
            for bl_type in self.bl_types:
                data_collection_name = BL_TYPE_DATAPATH.get(bl_type)
                setattr(
                    data_to,
                    data_collection_name,
                    [
                        name
                        for name in getattr(data_from, data_collection_name)
                    ],
                )

                # Keep imported datablocks names
                loaded_data_collections.add(data_collection_name)

        # Convert datablocks names to datablocks references
        datablocks = set()
        for collection_name in loaded_data_collections:
            datablocks.update(getattr(data_to, collection_name))

            # Remove fake user from loaded datablocks
            datacol = getattr(bpy.data, collection_name)
            seq = [
                False if d in datablocks else d.use_fake_user for d in datacol
            ]
            datacol.foreach_set("use_fake_user", seq)

        if self.bl_types & BL_OUTLINER_TYPES:
            # Get the right asset container from imported collections.
            outliner_entity = next(
                (
                    entity
                    for entity in list(data_to.collections)
                    + list(data_to.objects)
                    if entity.name.startswith(container_name)
                ),
                None,
            )

            if outliner_entity:
                # Create override for the library collection and its elements
                if do_override:
                    outliner_entity = (
                        outliner_entity.override_hierarchy_create(
                            bpy.context.scene,
                            bpy.context.view_layer
                            # NOTE After BL3.4: do_fully_editable=True
                        )
                    )

                    # Update datablocks because could have been renamed
                    datablocks = set(
                        outliner_entity.children_recursive
                    )
                    if isinstance(outliner_entity, bpy.types.Collection):
                        datablocks.update(set(outliner_entity.all_objects))
                    datablocks.add(outliner_entity)

                    # Ensure user override NOTE: will be unecessary after BL3.4
                    for d in datablocks:
                        if hasattr(d.override_library, "is_system_override"):
                            d.override_library.is_system_override = False

                # Set color
                if hasattr(outliner_entity, "color_tag"):
                    outliner_entity.color_tag = self.color_tag

                # Substitute name in case renamed with .###
                container_name = outliner_entity.name
        else:
            outliner_entity = None

        # Put into container
        container = self._containerize_datablocks(
            container_name, datablocks, container=container
        )

        # Set data to container
        container.library = bpy.data.libraries.get(libpath.name)
        container.outliner_entity = outliner_entity

        return container, datablocks

    def _containerize_datablocks(
        self,
        container_name: str,
        datablocks: List[bpy.types.ID],
        container: OpenpypeContainer = None,
    ) -> OpenpypeContainer:
        """Associate datablocks to a container. Create one if needed.

        Args:
            container_name (str): Name of container to be loaded.
            datablocks (List[bpy.types.ID]): Datablocks to filter and link to
                container collection
            container (OpenpypeContainer): Load into existing container.
                Defaults to None.

        Returns:
            OpenpypeContainer: Created container
        """
        if container:
            # Add datablocks to container
            add_datablocks_to_container(datablocks, container)

            # Rename container
            if container.name != container_name:
                container.name = container_name
        else:
            # Create container if none providen
            container = create_container(container_name, datablocks)

        return container

    def _load_fbx(self, libpath, container_name):
        """Load fbx process."""

        current_objects = set(bpy.data.objects)

        bpy.ops.import_scene.fbx(filepath=libpath)

        objects = set(bpy.data.objects) - current_objects

        for obj in objects:
            for collection in obj.users_collection:
                collection.objects.unlink(obj)

        container_collection = bpy.data.collections.get(container_name)
        link_to_collection(objects, container_collection)

        orphans_purge()
        deselect_all()

    def _link_blend(
        self,
        libpath: Path,
        container_name: str,
        container: OpenpypeContainer = None,
        override=True
    ) -> Tuple[OpenpypeContainer, List[bpy.types.ID]]:
        """Link blend process.

        Args:
            libpath (Path): Path of library to link.
            container_name (str): Name of container to link.
            container (OpenpypeContainer): Load into existing container.
                Defaults to None.
            override (bool, optional): Apply library override to linked
                datablocks. Defaults to True.

        Returns:
            Tuple[List[bpy.types.ID], OpenpypeContainer]:
                (Created scene container, Linked datablocks)
        """
        # Load collections from libpath library.
        container, all_datablocks = self._load_library_datablocks(
            libpath, container_name, container=container, do_override=override
        )

        container_collection = container.outliner_entity
        if container_collection:
            # If override_hierarchy_create method is not implemented for older
            # Blender versions we need the following steps.
            if not hasattr(container_collection, "override_hierarchy_create"):
                link_to_collection(
                    container_collection, bpy.context.scene.collection
                )
                container_collection = container_collection.override_create(
                    remap_local_usages=True
                )

                for child in get_children_recursive(container_collection):
                    child.override_create(remap_local_usages=True)

                for obj in set(container_collection.all_objects):
                    obj.override_create(remap_local_usages=True)

                # force remap to fix modifers, constaints and drivers targets.
                for obj in set(container_collection.all_objects):
                    obj.override_library.reference.user_remap(obj.id_data)

        return container, all_datablocks

    def _append_blend(
        self,
        libpath: Path,
        container_name: str,
        container: OpenpypeContainer = None
    ) -> Tuple[OpenpypeContainer, List[bpy.types.ID]]:
        """Append blend process.

        Args:
            libpath (Path): Path of library to append.
            container_name (str): Name of container to append.
            container (OpenpypeContainer): Load into existing container.
                Defaults to None.

        Returns:
            Tuple[List[bpy.types.ID], OpenpypeContainer]:
                (Created scene container, Appended datablocks)
        """
        # Load collections from libpath library.
        container, all_datablocks = self._load_library_datablocks(
            libpath, container_name, container=container, link=False
        )

        # Link loaded collection to scene
        container_collection = container.outliner_entity
        if container_collection:
            link_to_collection(
                container_collection, bpy.context.scene.collection
            )

        return container, all_datablocks

    def _instance_blend(
        self,
        libpath: Path,
        container_name: str,
        container: OpenpypeContainer = None
    ) -> Tuple[OpenpypeContainer, List[bpy.types.ID]]:
        """Instance blend process.

        An instance is basically a linked collection
        instanced by an object in the outliner.

        Args:
            libpath (Path): Path of library to instance.
            container_name (str): Name of container to instance.
            container (OpenpypeContainer): Load into existing container.
                Defaults to None.

        Returns:
            Tuple[List[bpy.types.ID], OpenpypeContainer]: 
                (Created scene container, Linked datablocks)
        """
        container, all_datablocks = self._link_blend(
            libpath, container_name, container=container, override=False
        )

        # Avoid duplicates between instance and collection
        if bpy.data.collections.get(container.name):
            instance_object_name = f"{container.name}.001"
        else:
            instance_object_name = container.name

        # Create empty object
        instance_object = bpy.data.objects.new(
            instance_object_name, object_data=None
        )
        bpy.context.scene.collection.objects.link(instance_object)

        # Instance collection to object
        instance_object.instance_collection = container.outliner_entity
        instance_object.instance_type = "COLLECTION"
        container.outliner_entity = instance_object

        # Keep instance object as only datablock
        container.datablock_refs.clear()
        instance_ref = container.datablock_refs.add()
        instance_ref.datablock = instance_object

        return container, all_datablocks

    def _apply_options(self, asset_group, options):
        """Can be implemented by a sub-class"""
        pass

    def get_load_function(self) -> Callable:
        """Get appropriate function regarding the load type of the loader.

        Raises:
            ValueError: load_type has not a correct value. Must be
                APPEND, INSTANCE or LINK.

        Returns:
            Callable: Load function
        """
        if self.load_type == "APPEND":
            return self._append_blend
        elif self.load_type == "INSTANCE":
            return self._instance_blend
        elif self.load_type == "LINK":
            return self._link_blend
        else:
            raise ValueError(
                "'load_type' attribute must be set by loader subclass to:"
                "APPEND, INSTANCE or LINK."
            )

    @exec_process
    def load(
        self,
        context: dict,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[OpenpypeContainer, List[bpy.types.ID]]:
        """Load asset via database.

        Args:
            context: Full parenthood of representation to load
            name: Subset name
            namespace: Use pre-defined namespace
            options: Additional settings dictionary

        Returns:
            Tuple[OpenpypeContainer, List[bpy.types.ID]]:
                (Container, Datablocks)
        """
        assert Path(self.fname).exists(), f"{self.fname} doesn't exist."
        libpath = Path(self.fname)

        asset = context["asset"]["name"]
        container_basename = build_op_basename(asset, name)

        # Pick load function and execute
        load_func = self.get_load_function()
        container, datablocks = load_func(libpath, container_basename)

        # Stop if no container
        if not container:
            return container, datablocks

        # Ensure container metadata
        if not container.get(AVALON_PROPERTY):
            metadata_update(
                container,
                {
                    "schema": "openpype:container-2.0",
                    "id": AVALON_CONTAINER_ID,
                    "name": context["subset"]["name"],
                    "namespace": namespace or "",
                    "loader": self.__class__.__name__,
                    "representation": str(context["representation"]["_id"]),
                    "libpath": libpath.as_posix(),
                    "asset_name": context["asset"]["name"],
                    "parent": str(context["representation"]["parent"]),
                    "family": context["representation"]["context"]["family"],
                    "objectName": container.name,
                },
            )

        # Apply options
        if options is not None:
            self._apply_options(container, options)

        # Clear and purge useless datablocks.
        orphans_purge()

        self[:] = list(datablocks)
        return container, datablocks

    @exec_process
    def update(
        self, container_metadata: Dict, representation: Dict
    ) -> Tuple[OpenpypeContainer, List[bpy.types.ID]]:
        """Update container with representation.

        Args:
            container_metadata (Dict): Data of container to switch.
            representation (Dict): Representation doc to replace
                container with.

        Returns:
            Tuple[OpenpypeContainer, List[bpy.types.ID]]:
                (Container, Datablocks)
        """
        object_name = container_metadata["objectName"]
        container = self._get_scene_container(container_metadata)
        assert container, f"The asset is not loaded: {object_name}"

        new_libpath = Path(get_representation_path(representation))
        assert (
            new_libpath.exists()
        ), f"No library file found for representation: {representation}"

        self.log.info(
            "Container: %s\nRepresentation: %s",
            pformat(container, indent=2),
            pformat(representation, indent=2),
        )

        # Process container replacement
        container_basename = build_op_basename(
            container_metadata["asset_name"], container_metadata["name"]
        )
        container, datablocks = self.replace_container(
            container, new_libpath, container_basename
        )

        # update metadata
        metadata_update(
            container,
            {
                "libpath": new_libpath.as_posix(),
                "representation": str(representation["_id"]),
            },
        )
        return container, datablocks

    def replace_container(
        self,
        container: OpenpypeContainer,
        new_libpath: Path,
        new_container_name: str,
    ) -> Tuple[OpenpypeContainer, List[bpy.types.ID]]:
        """Replace container with datablocks from given libpath.

        Args:
            container (OpenpypeContainer): Container to replace datablocks of.
            new_libpath (Path): Library path to load datablocks from.
            new_container_name (str): Name of new container to load.

        Returns:
            Tuple[OpenpypeContainer, List[bpy.types.ID]]:
                (Container, List of loaded datablocks)
        """
        load_func = self.get_load_function()

        # Update the asset group with maintained contexts.
        container_metadata = container.get(AVALON_PROPERTY, {})

        # Check is same loader than the previous load
        same_loader = self.__class__.__name__ == container_metadata.get(
            "loader"
        )

        # In case several containers share same library
        library_multireferenced = any(
            [
                c
                for c in bpy.context.scene.openpype_containers
                if c != container and c.library is container.library
            ]
        )

        # In special configuration, optimization by changing the library
        if (
            same_loader
            and self.load_type in ("INSTANCE", "LINK")
            and not library_multireferenced
        ):
            # Keep current datablocks
            old_datablocks = {
                d_ref.datablock for d_ref in container.datablock_refs
            }

            # Relink library
            container.library.filepath = new_libpath.as_posix()
            container.library.reload()
            container.library.name = new_libpath.name

            # Substitute library to keep reference
            # if purged because duplicate references
            container.library = (
                container.outliner_entity.override_library.reference.library
                if self.load_type == "LINK"
                else container.outliner_entity.instance_collection.library
            )

            datablocks = [
                d_ref.datablock for d_ref in container.datablock_refs
            ]
        else:
            # Default behaviour to wipe and reload everything
            # but keeping same container
            if container.outliner_entity:
                parent_collection = get_parent_collection(
                    container.outliner_entity
                )
            else:
                parent_collection = None

            # Keep current datablocks
            old_datablocks = {
                d_ref.datablock for d_ref in container.datablock_refs
            }

            # Clear container datablocks
            container.datablock_refs.clear()

            # Load new into same container
            container, datablocks = load_func(
                new_libpath,
                new_container_name,
                container=container,
            )

            # Old datablocks remap and deletion
            for old_datablock in old_datablocks:
                # Find matching new datablock by name without .###
                new_datablock = next(
                    (
                        d
                        for d in datablocks
                        if old_datablock.name.rstrip(f".{digits}")
                        == d.name.rstrip(f".{digits}")
                    ),
                    None,
                )

                # Replace old by new datablock and keep the original name.
                if new_datablock:
                    original_datablock_name = old_datablock.name
                    old_datablock.name += ".old"
                    new_datablock.name = original_datablock_name
                    old_datablock.user_remap(new_datablock)

            # Restore parent collection if existing
            if parent_collection:
                unlink_from_collection(
                    container.outliner_entity,
                    bpy.context.scene.collection
                )
                link_to_collection(
                    container.outliner_entity,
                    parent_collection
                )

        # Clear and purge useless datablocks.
        orphans_purge()

        # Update override library operations from asset objects if available.
        for obj in get_container_objects(container):
            if getattr(obj.override_library, "operations_update", None):
                obj.override_library.operations_update()

        return container, datablocks

    @exec_process
    def switch(
        self, container_metadata: Dict, representation: Dict
    ) -> Tuple[OpenpypeContainer, List[bpy.types.ID]]:
        """Switch container with representation.

        Args:
            container_metadata (Dict): Data of container to switch.
            representation (Dict): Representation doc to replace
                container with.

        Returns:
            Tuple[OpenpypeContainer, List[bpy.types.ID]]:
                (Container, List of loaded datablocks)
        """
        object_name = container_metadata["objectName"]
        container = self._get_scene_container(container_metadata)
        assert container, f"The asset is not loaded: {object_name}"

        new_libpath = Path(get_representation_path(representation))
        assert (
            new_libpath.exists()
        ), f"No library file found for representation: {representation}"

        self.log.info(
            "Container: %s\nRepresentation: %s",
            pformat(container, indent=2),
            pformat(representation, indent=2),
        )

        # Build container base name
        asset_name = representation["context"]["asset"]
        subset_name = representation["context"]["subset"]
        container_basename = build_op_basename(asset_name, subset_name)

        # Replace container
        container, datablocks = self.replace_container(
            container, new_libpath, container_basename
        )

        # update metadata
        metadata_update(
            container,
            {
                "name": subset_name,
                "namespace": container.get(AVALON_PROPERTY, {}).get(
                    "namespace", ""
                ),
                "loader": self.__class__.__name__,
                "representation": str(representation["_id"]),
                "libpath": new_libpath.as_posix(),
                "asset_name": asset_name,
                "parent": str(representation["parent"]),
                "family": representation["context"]["family"],
                "objectName": container.name,
            },
        )

        return container, datablocks

    @exec_process
    def remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container: Container to remove.

        Returns:
            Whether the container was deleted.
        """
        scene_container = self._get_scene_container(container)

        if not scene_container:
            return False

        remove_container(scene_container)

        return True


class StructDescriptor:
    """Generic Descriptor to store and restor properties from blender struct.
    """

    _invalid_property_names = [
        "__doc__",
        "__module__",
        "__slots__",
        "bl_rna",
        "rna_type",
        "name",
        "type",
        "is_override_data",
        "vertex_indices_set",
    ]

    def _get_from_bpy_data(self, prop_value: Dict):
        if (
            prop_value.get("class") is bpy.types.Object
            and bpy.context.scene.objects.get(prop_value.get("name"))
        ):
            return bpy.context.scene.objects.get(prop_value.get("name"))
        else:
            for _, data_member in getmembers(bpy.data):
                if (
                    isinstance(data_member, bpy.types.bpy_prop_collection)
                    and isinstance(
                        data_member.get(prop_value.get("name")),
                        prop_value.get("class"),
                    )
                ):
                    return data_member.get(prop_value.get("name"))

    def get_object(self):
        return (
            bpy.context.scene.objects.get(self.object_name)
            or bpy.data.objects.get(self.object_name)
        )

    def store_property(self, prop_name, prop_value):
        if isinstance(prop_value, bpy.types.ID):
            prop_value = {
                "class": prop_value.__class__,
                "name": prop_value.name,
            }
        elif isinstance(prop_value, Matrix):
            prop_value = prop_value.copy()
        self.properties[prop_name] = prop_value

    def restore_property(self, entity, prop_name):
        prop_value = self.properties.get(prop_name)

        # get property value as bpy.types.{class} if needed.
        if (
            isinstance(prop_value, dict)
            and prop_value.get("class")
            and prop_value.get("name")
        ):
            prop_value = self._get_from_bpy_data(prop_value)

        try:
            setattr(entity, prop_name, prop_value)
        except Exception as error:
            log.warning(
                "restore_property failed:"
                f" >>> {entity.name}.{prop_name}={prop_value}"
                f" *** {error}"
            )

    def __init__(self, bpy_struct: bpy.types.bpy_struct):
        self.name = bpy_struct.name
        self.type = bpy_struct.type
        self.object_name = bpy_struct.id_data.name
        self.is_override_data = getattr(bpy_struct, "is_override_data", True)

        self.properties = dict()
        for prop_name, prop_value in getmembers(bpy_struct):
            # filter the property
            if (
                prop_name in self._invalid_property_names
                or bpy_struct.is_property_readonly(prop_name)
            ):
                continue
            # store the property
            if (
                not self.is_override_data
                or bpy_struct.is_property_overridable_library(prop_name)
            ):
                self.store_property(prop_name, prop_value)


class ModifierDescriptor(StructDescriptor):
    """Store the name, type, properties and object of a modifier."""

    def __init__(self, bpy_struct: bpy.types.bpy_struct):
        super().__init__(bpy_struct)

        self.order_index = bpy_struct.id_data.modifiers.find(self.name)

    def restor(self):
        obj = self.get_object()
        if obj:
            modifier = obj.modifiers.get(self.name)
            if not modifier and not self.is_override_data:
                modifier = obj.modifiers.new(
                    self.name,
                    self.type,
                )
            if modifier and modifier.type == self.type:
                for prop_name in self.properties:
                    self.restore_property(modifier, prop_name)

    def reorder(self):
        obj = self.get_object()
        if obj:
            current_index = obj.modifiers.find(self.name)
            if current_index > self.order_index > -1:
                while current_index > self.order_index:
                    with context_override(active=obj, selected=obj):
                        ops_result = bpy.ops.object.modifier_move_up(
                            modifier=self.name,
                        )
                    current_index = obj.modifiers.find(self.name)
                    if "CANCELLED" in ops_result:
                        break


class ConstraintDescriptor(StructDescriptor):
    """Store the name, type, properties and object of a constraint."""

    def restor(self, bone_name=None):
        obj = self.get_object()
        if bone_name:
            if obj and obj.type == "ARMATURE":
                obj = obj.pose.bones.get(bone_name)
            else:
                return
        if obj:
            constraint = obj.constraints.get(self.name)
            if not constraint and not self.is_override_data:
                constraint = obj.constraints.new(self.type)
                constraint.name = self.name
            if constraint and constraint.type == self.type:
                for prop_name in self.properties:
                    self.restore_property(constraint, prop_name)
