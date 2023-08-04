"""Shared functionalities for Blender files data manipulation."""
import itertools
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Iterator
from collections.abc import Iterable

import bpy
from openpype.client.entities import get_representations
from openpype.pipeline.constants import AVALON_CONTAINER_ID, AVALON_INSTANCE_ID
from openpype.pipeline.context_tools import get_current_project_name
from openpype.pipeline.load.plugins import (
    LoaderPlugin,
    discover_loader_plugins,
)
from openpype.pipeline.load.utils import loaders_from_repre_context


# Key for metadata dict
AVALON_PROPERTY = "avalon"

# Match Blender type to a datapath to look into. Needed for native UI creator.
BL_TYPE_DATAPATH = (  # TODO rename DATACOL
    {  # NOTE Order is important for some hierarchy based processes!
        bpy.types.Collection: "collections",  # NOTE Must be always first
        bpy.types.Object: "objects",
        bpy.types.Camera: "cameras",
        bpy.types.Action: "actions",
        bpy.types.Armature: "armatures",
    }
)
# Match Blender type to an ICON for display
BL_TYPE_ICON = {
    bpy.types.Collection: "OUTLINER_COLLECTION",
    bpy.types.Object: "OBJECT_DATA",
    bpy.types.Camera: "CAMERA_DATA",
    bpy.types.Action: "ACTION",
    bpy.types.Armature: "ARMATURE_DATA",
}
# Types which can be handled through the outliner
BL_OUTLINER_TYPES = frozenset((bpy.types.Collection, bpy.types.Object))


def ensure_unique_name(name: str, list_of_existing_names: Set[str]) -> str:
    """Return a unique name based on the name passed in.

    Args:
        name (str): Name to make unique.
        list_of_existing_names (Set[str]): List of existing names.

    Returns:
        str: Unique name.
    """
    # Cast to set
    if not isinstance(list_of_existing_names, set):
        list_of_existing_names = set(list_of_existing_names)

    # Guess basename and extension
    split_name = name.rsplit(".", 1)
    if len(split_name) > 1 and split_name[1].isdigit():
        basename, number = split_name
        extension_i = int(number) + 1
    else:
        basename = split_name[0]
        extension_i = 1

    # Increment extension based on existing ones
    while name in list_of_existing_names:
        name = f"{basename}.{extension_i:0>3}"
        extension_i += 1

    return name


def build_op_basename(
    asset: str, subset: str, namespace: Optional[str] = None
) -> str:
    """Return a consistent name for an asset."""
    name = f"{asset}"
    if namespace:
        name = f"{name}_{namespace}"
    name = f"{name}_{subset}"
    return name


def get_children_recursive(
    entity: Union[bpy.types.Collection, bpy.types.Object]
) -> Iterator[Union[bpy.types.Collection, bpy.types.Object]]:
    """Get childrens recursively from a object or a collection.

    Arguments:
        entity: The parent entity.

    Yields:
        The next childrens from parent entity.
    """
    # Since Blender 3.1.0 we can use "children_recursive" attribute.
    if hasattr(entity, "children_recursive"):
        for child in entity.children_recursive:
            yield child
    else:
        for child in entity.children:
            yield child
            yield from get_children_recursive(child)


def get_all_outliner_children(
    entity: Union[bpy.types.Collection, bpy.types.Object]
) -> Set[Union[bpy.types.Collection, bpy.types.Object]]:
    """Get all outliner children of an outliner entity.

    For a Collection, it is both objects and children collections.
    For an Object, only objects parented to the given one.

    Args:
        entity (Union[bpy.types.Collection, bpy.types.Object]): Outliner entity to get children from.

    Returns:
        Set[Union[bpy.types.Collection, bpy.types.Object]]: All outliner children.
    """
    if not entity:
        return set()
    elif not isinstance(entity, tuple(BL_OUTLINER_TYPES)):
        raise TypeError(
            f"{entity} is not an accepted outliner type: {BL_OUTLINER_TYPES}"
        )
    elif hasattr(entity, "all_objects"):
        return set(entity.children_recursive) | set(entity.all_objects)
    else:
        return set(entity.children_recursive)


def get_parent_collection(
    entity: Union[bpy.types.Collection, bpy.types.Object],
) -> Optional[bpy.types.Collection]:
    """Get the parent of the input outliner entity (collection or object).

    Args:
        entity (Union[bpy.types.Collection, bpy.types.Object]):
            Collection to get parent of.

    Returns:
        Optional[bpy.types.Collection]: Parent of entity
    """
    scene_collection = bpy.context.scene.collection
    if entity in scene_collection.children.values():
        return scene_collection
    # Entity is a Collection.
    elif isinstance(entity, bpy.types.Collection):
        for col in scene_collection.children_recursive:
            if entity in col.children.values():
                return col
    # Entity is an Object.
    elif isinstance(entity, bpy.types.Object):
        for col in scene_collection.children_recursive:
            if entity in col.objects.values():
                return col


def get_instanced_collections() -> Set[bpy.types.Collection]:
    """Get all instanced collections from context scene.

    Returns:
        Set[bpy.types.Collection]: Instanced collections in current scene.
    """
    return {
        obj.instance_collection
        for obj in bpy.context.scene.objects
        if obj.is_instancer
        and obj.instance_collection
        and obj.instance_collection.library
    }


def link_to_collection(
    entity: Union[bpy.types.Collection, bpy.types.Object, Iterator],
    collection: bpy.types.Collection,
):
    """link an entity to a collection.

    Note:
        Recursive function if entity is iterable.

    Arguments:
        entity: The collection, object or list of valid entities who need to be
            parenting with the given collection.
        collection: The collection used for parenting.
    """
    # Entity is Iterable, execute function recursively.
    if isinstance(entity, Iterable):
        for i in entity:
            link_to_collection(i, collection)
    # Entity is a Collection.
    elif (
        isinstance(entity, bpy.types.Collection)
        and entity not in collection.children.values()
        and collection not in entity.children.values()
        and entity is not collection
    ):
        collection.children.link(entity)
    # Entity is an Object.
    elif (
        isinstance(entity, bpy.types.Object)
        and entity not in collection.objects.values()
        and entity.instance_collection is not collection
        and entity.instance_collection
        not in set(get_children_recursive(collection))
    ):
        collection.objects.link(entity)


def unlink_from_collection(
    entity: Union[bpy.types.Collection, bpy.types.Object, Iterator],
    collection: bpy.types.Collection,
):
    """Unlink an entity from a collection.

    Note:
        Recursive function if entity is iterable.

    Args:
        entity (Union[bpy.types.Collection, bpy.types.Object, Iterator]): The collection, object or list of valid entities who need to be
            parenting with the given collection.
        collection (bpy.types.Collection): The collection to remove parenting.
    """
    # Entity is Iterable, execute function recursively.
    if isinstance(entity, Iterable):
        for i in entity:
            unlink_from_collection(i, collection)
    # Entity is a Collection.
    elif isinstance(entity, bpy.types.Collection) and entity is not collection:
        collection.children.unlink(entity)
    # Entity is an Object.
    elif isinstance(entity, bpy.types.Object):
        collection.objects.unlink(entity)


def get_loader_by_name(loaders: List[LoaderPlugin], load_type: str) -> str:
    """Get loader name from list by requested load type.

    Args:
        loaders (List[LoaderPlugin]): List of available loaders
        load_type (str): Load type to get loader of

    Returns:
        str: Loader name
    """
    return next(
        (l for l in loaders if l.__name__.startswith(load_type)),
        None,
    )


def assign_loader_to_datablocks(
    datablocks: List[bpy.types.ID],
) -> Dict[bpy.types.ID, LoaderPlugin]:
    """Assign loader name to container datablocks loaded outside of OP.

    For example if you link a container using Blender's file tools.

    Args:
        datablocks (List[bpy.types.ID]): Datablocks to assign loader to.
    """
    datablocks_to_skip = set()
    all_loaders = discover_loader_plugins()
    all_instanced_collections = get_instanced_collections()
    containers_loaders = {}

    # Get all representations in scene in one DB call
    project_name = get_current_project_name()
    representations = {
        str(repre_doc["_id"]): repre_doc
        for repre_doc in get_representations(
            project_name,
            representation_ids={
                d[AVALON_PROPERTY]["representation"]
                for d in datablocks
                if d.get(AVALON_PROPERTY)
            },
        )
    }

    # Assign loaders to containers
    for datablock in datablocks:
        if datablock in datablocks_to_skip:
            continue

        # Get avalon data
        avalon_data = datablock.get(AVALON_PROPERTY)
        if (
            not avalon_data
            or avalon_data.get("id") == AVALON_INSTANCE_ID
            or avalon_data.get("loader")
        ):
            continue

        # Skip all children of container
        if hasattr(datablock, "children_recursive"):
            datablocks_to_skip.update(datablock.children_recursive)
        if hasattr(datablock, "all_objects"):
            datablocks_to_skip.update(datablock.all_objects)

        # Build fake representation context
        fake_repre_context = {
            "project": {
                "name": project_name,
            },
            "subset": {
                "data": {"family": avalon_data["family"]},
                "schema": "openpype:subset-3.0",
            },
            "representation": representations.get(
                avalon_data["representation"]
            ),
        }
        # Get available loaders
        loaders = loaders_from_repre_context(all_loaders, fake_repre_context)
        if datablock.library or datablock.override_library:
            # Instance loader, an instance in OP is necessarily a link
            loader_type = (
                "Instance"
                if datablock in all_instanced_collections
                else "Link"
            )
        else:  # Append loader
            loader_type = "Append"

        # Get loader
        loader = get_loader_by_name(loaders, loader_type)
        if loader:
            datablock[AVALON_PROPERTY]["loader"] = loader.__name__ or ""
        containers_loaders[datablock] = loader

    return containers_loaders


def transfer_stack(
    source_datablock: bpy.types.ID,
    stack_name: str,
    target_datablock: bpy.types.ID,
):
    """Transfer stack of modifiers or constraints from a datablock to another one.

    New stack entities are created for each source stack entity.
    If a stack entity in the target datablock has the same name of one
    from the source datablock, it is skipped. No duplicate created, neither
    attribute update.

    Args:
        src_datablock (bpy.types.ID): Datablock to get stack from.
        stack_name (str): Stack name to transfer (eg 'modifiers', 'constraints'...)
        target_datablock (bpy.types.ID): Datablock to create stack entities to
    """
    src_col = getattr(source_datablock, stack_name)
    for stack_datablock in src_col:
        if stack_datablock.is_override_data:
            continue

        target_col = getattr(target_datablock, stack_name)
        target_stack_datablock = target_col.get(stack_datablock.name)
        if not target_stack_datablock:
            if stack_name == "modifiers":
                target_stack_datablock = target_col.new(
                    stack_datablock.name, stack_datablock.type
                )
            else:
                target_stack_datablock = target_col.new(stack_datablock.type)

            # Transfer attributes
            attributes = {
                a
                for a in dir(stack_datablock)
                if not a.startswith("_")
                and a != "bl_rna"
                and not callable(getattr(stack_datablock, a))
                and hasattr(target_stack_datablock, a)
                and not target_stack_datablock.is_property_readonly(a)
            }
            for attr in attributes:
                setattr(
                    target_stack_datablock,
                    attr,
                    getattr(stack_datablock, attr),
                )


def get_datablocks_with_filepath(
    absolute=True, relative=True
) -> Set[bpy.types.ID]:
    """Get all datablocks with filepaths.

    Args:
        absolute (bool, optional): Get datablocks with absolute paths.
            Defaults to True.
        relative (bool, optional): Get datablocks with relative paths.
            Defaults to True.

    Returns:
        Set[bpy.types.ID]: Datablocks with filepaths.
    """
    datablocks = set()
    for data_name in dir(bpy.data):
        data_collection = getattr(bpy.data, data_name)
        if not isinstance(data_collection, bpy.types.bpy_prop_collection):
            continue
        for datablock in data_collection.values():
            if (
                datablock
                and hasattr(datablock, "filepath")
                and not datablock.is_property_readonly("filepath")
                and datablock.filepath != ""
                and not datablock.library
                and not datablock.is_library_indirect
                and not (
                    isinstance(datablock, bpy.types.Image)
                    and datablock.packed_file
                )
            ):
                if relative and datablock.filepath.startswith("//"):
                    datablocks.add(datablock)
                elif absolute and not datablock.filepath.startswith("//"):
                    datablocks.add(datablock)
    return datablocks


def make_paths_absolute(source_filepath: Path = None):
    """Make all paths absolute for datablock in current blend file.

    Args:
        source_filepath (Path, optional): Filepath to remap paths from,
            in case file copy has been executed without paths remapping.
            Defaults to None.

    Returns:
        Set[bpy.types.ID]: Remapped datablocks.
    """
    relative_datablocks = get_datablocks_with_filepath(absolute=False)
    remapped_datablocks = set()
    if source_filepath:
        for d in relative_datablocks:
            try:
                d.filepath = str(
                    Path(
                        bpy.path.abspath(
                            d.filepath,
                            start=source_filepath.parent,
                        )
                    ).resolve()
                )
                remapped_datablocks.add(d)
            except (RuntimeError, ReferenceError, OSError) as err:
                print(err)

    bpy.ops.file.make_paths_absolute()

    return remapped_datablocks


def get_root_datablocks(
    datablocks: List[bpy.types.ID],
    types: Union[bpy.types.ID, Iterable[bpy.types.ID]] = None,
) -> Set[bpy.types.ID]:
    """Get the root datablocks from a sequence of datablocks.

    A root datablock is the first datablock of the hierarchy that is not
    referenced by another datablock in the given list.

    Args:
        types (Iterable): List of types to filter the datablocks

    Returns:
        bpy.types.ID: Root datablock
    """
    # Put into iterable if not
    if types is not None and not isinstance(types, Iterable):
        types = (types,)

    return {
        d
        for d, users in bpy.data.user_map(subset=datablocks).items()
        if (types is None or isinstance(d, tuple(types)))
        and not users & set(datablocks)
    }


def get_all_datablocks():
    """Get all datablocks from the current blend file.

    Returns:
        Set[bpy.types.ID]: All datablocks
    """
    all_datablocks = set()
    for bl_type in dir(bpy.data):
        if not bl_type.startswith("_"):
            datacol = getattr(bpy.data, bl_type)
            if isinstance(datacol, bpy.types.bpy_prop_collection) and len(
                bl_type
            ):
                all_datablocks.update(getattr(bpy.data, bl_type))
    return all_datablocks


def get_used_datablocks(
    user_datablocks: Set[bpy.types.ID],
) -> Set[bpy.types.ID]:
    """Get all datablocks that are used by the given datablocks.

    Args:
        user_datablocks (Set[bpy.types.ID]):
            Datablocks to get used datablocks from

    Returns:
        Set[bpy.types.ID]: Used datablocks
    """
    return {
        d
        for d, users in bpy.data.user_map(
            subset=itertools.chain.from_iterable(
                getattr(bpy.data, datacol)
                for datacol in dir(bpy.data)
                if not datacol.startswith("_")
                and isinstance(
                    getattr(bpy.data, datacol), bpy.types.bpy_prop_collection
                )
                and not callable(getattr(bpy.data, datacol))
            )
        ).items()
        if users & user_datablocks
    }
