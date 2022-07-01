"""Shared functionality for pipeline plugins for Blender."""

from pprint import pformat
from inspect import getmembers
from pathlib import Path
from contextlib import contextmanager, ExitStack
from typing import Dict, List, Optional, Union, Iterator
from collections.abc import Iterable
from bson.objectid import ObjectId

import bpy
from mathutils import Matrix

from openpype.api import Logger
from openpype.pipeline import (
    legacy_io,
    LegacyCreator,
    LoaderPlugin,
    get_representation_path,
    AVALON_CONTAINER_ID,
    AVALON_INSTANCE_ID,
)
from .ops import (
    MainThreadItem,
    execute_in_main_thread
)
from .lib import (
    imprint,
    get_selection
)
from .pipeline import metadata_update, AVALON_PROPERTY, MODEL_DOWNSTREAM


VALID_EXTENSIONS = [".blend", ".json", ".abc", ".fbx"]

log = Logger.get_logger(__name__)


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


def create_blender_context(
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

    override_context = bpy.context.copy()

    windows = [window] if window else bpy.context.window_manager.windows

    for win in windows:
        for area in win.screen.areas:
            if area.type == area_type:
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


def create_container(
    name: str,
    color_tag: Optional[str] = None
) -> Optional[bpy.types.Collection]:
    """Create the collection container with the given name.

    Arguments:
        name:  The name of the collection.
        color_tag: The display color in the outliner.

    Returns:
        The collection if successed, None otherwise.
    """
    if bpy.data.collections.get(name) is None:
        container = bpy.data.collections.new(name)
        if color_tag and hasattr(container, "color_tag"):
            container.color_tag = color_tag
        bpy.context.scene.collection.children.link(container)
        return container


def remove_container(
    container: Union[bpy.types.Collection, bpy.types.Object],
    content_only: Optional[bool] = False
):
    """Remove the container with all this objects and child collections.

    Arguments:
        container: The collection or empty container to be removed.
        content_only: Remove all the container content but keep the container
            collection or empty. Default to False.

    Note:
        This rename all removed elements with .removed suffix to prevent
        naming conflict with created object before calling orphans_purge.
    """
    objects_to_remove = set()
    collections_to_remove = set()
    data_to_remove = set()
    materials_to_remove = set()

    if isinstance(container, bpy.types.Collection):
        # Append all objects in container collection to be removed.
        for obj in set(container.all_objects):
            objects_to_remove.add(obj)
            # Append original object if exists.
            if obj.original:
                objects_to_remove.add(obj.original)
        # Append all child collections in container to be removed.
        for child in set(get_children_recursive(container)):
            collections_to_remove.add(child)
        # Append the container collection if content_only is False.
        if not content_only:
            collections_to_remove.add(container)
    else:
        # Append all child objects in container object.
        for obj in set(get_children_recursive(container)):
            objects_to_remove.add(obj)
        # Append the container object if content_only is False.
        if not content_only:
            objects_to_remove.add(container)

    # Remove objects
    for obj in objects_to_remove:
        # Append object data if exists.
        if obj.data:
            data_to_remove.add(obj.data)
        obj.name = f"{obj.name}.removed"
        bpy.data.objects.remove(obj)
    # Remove collections
    for collection in collections_to_remove:
        collection.name = f"{collection.name}.removed"
        bpy.data.collections.remove(collection)
    # Remove data
    for data in data_to_remove:
        if data.users == 0:
            data.name = f"{data.name}.removed"
            # Append materials if data is mesh.
            if isinstance(data, bpy.types.Mesh):
                for mtl in data.materials:
                    if mtl:
                        materials_to_remove.add(mtl)
            # Remove data from this data collection type.
            for data_collection in (
                bpy.data.meshes,
                bpy.data.curves,
                bpy.data.lights,
                bpy.data.cameras,
                bpy.data.armatures,
            ):
                if data in data_collection.values():
                    data_collection.remove(data)
    # Remove materials
    for mtl in materials_to_remove:
        if mtl.users == 0:
            mtl.name = f"{mtl.name}.removed"
            bpy.data.materials.remove(mtl)


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
    if isinstance(container, bpy.types.Collection):
        objects = list(container.all_objects)
    else:
        objects = list(get_children_recursive(container))
        objects.append(container)
    return objects


def get_parent_collection(
    collection: bpy.types.Collection
) -> Optional[bpy.types.Collection]:
    """Get the parent of the input collection."""
    check_list = [bpy.context.scene.collection]
    for c in check_list:
        if collection.name in c.children.keys():
            return c
        check_list.extend(c.children)

    return None


def get_main_collection() -> bpy.types.Collection:
    """Get the main collection from scene.
    - the scene root collection if has no children.
    - or the first avalon instance collection child of root collection,
        but no family 'camera', 'action' and 'pointcache'.

    Returns:
        The main collection.
    """
    _invalid_family = ("camera", "action", "pointcache")

    main_collection = bpy.context.scene.collection

    instance_collections = [
        child
        for child in main_collection.children
        if (
            child.get(AVALON_PROPERTY)
            and child[AVALON_PROPERTY].get("id") == AVALON_INSTANCE_ID
            and child[AVALON_PROPERTY].get("family") not in _invalid_family
        )
    ]
    if len(instance_collections) == 1:
        main_collection = instance_collections[0]

    return main_collection


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


def link_to_collection(
    entity: Union[bpy.types.Collection, bpy.types.Object, Iterator],
    collection: bpy.types.Collection
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
        and entity.instance_collection not in set(
            get_children_recursive(collection)
        )
    ):
        collection.objects.link(entity)


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
    while bpy.data.orphans_purge(do_local_ids=False, do_recursive=True):
        pass

    # clear unused libraries
    for library in list(bpy.data.libraries):
        if len(library.users_id) == 0:
            bpy.data.libraries.remove(library)


class ContainerMaintainer(ExitStack):
    """ContextManager to maintain all important properties
    when updating container.

    Arguments:
        container: Container to maintain after updating.
    """

    maintained_parameters = [
        "parent",
        "transforms",
        "modifiers",
        "constraints",
        "targets",
        "drivers",
        "actions",
    ]

    def __init__(
        self, container: Union[bpy.types.Collection, bpy.types.Object]
    ):
        super().__init__()
        self.container = container
        self.container_objects = set(get_container_objects(self.container))

    def __enter__(self):
        for parameter_name in self.maintained_parameters:
            maintainer = getattr(self, f"maintained_{parameter_name}", None)
            if maintainer:
                self.enter_context(maintainer(self.container_objects))

    @contextmanager
    def maintained_parent(self, objects):
        """Maintain parent during context."""
        scene_objects = set(bpy.context.scene.objects) - objects
        objects_parents = dict()
        for obj in scene_objects:
            if obj.parent in objects:
                objects_parents[obj.name] = {
                    "name": obj.parent.name,
                    "type": obj.parent_type,
                    "bone": obj.parent_bone,
                    "vertices": list(obj.parent_vertices),
                    "matrix_inverse": obj.matrix_parent_inverse.copy(),
                }
        for obj in objects:
            if obj.parent in scene_objects:
                objects_parents[obj.name] = {
                    "name": obj.parent.name,
                    "type": obj.parent_type,
                    "bone": obj.parent_bone,
                    "vertices": list(obj.parent_vertices),
                    "matrix_inverse": obj.matrix_parent_inverse.copy(),
                }
        try:
            yield
        finally:
            # Restor parent.
            for obj_name, parent_data in objects_parents.items():
                obj = bpy.context.scene.objects.get(obj_name)
                parent = bpy.context.scene.objects.get(parent_data["name"])
                if obj and parent and obj.parent is not parent:
                    obj.parent = parent
                    obj.parent_type = parent_data["type"]
                    obj.parent_bone = parent_data["bone"]
                    obj.parent_vertices = parent_data["vertices"]
                    obj.matrix_parent_inverse = parent_data["matrix_inverse"]

    @contextmanager
    def maintained_transforms(self, objects):
        """Maintain transforms during context."""
        # Store transforms for all objects in container.
        objects_transforms = {
            obj.name: obj.matrix_basis.copy()
            for obj in objects
        }
        # Store transforms for all bones from armatures in container.
        bones_transforms = {
            obj.name: {
                bone.name: bone.matrix_basis.copy()
                for bone in obj.pose.bones
            }
            for obj in objects
            if obj.type == "ARMATURE"
        }
        try:
            yield
        finally:
            # Restor transforms.
            for obj in set(bpy.context.scene.objects):
                if obj.name in objects_transforms:
                    obj.matrix_basis = objects_transforms[obj.name]
                # Restor transforms for bones from armature.
                if obj.type == "ARMATURE" and obj.name in bones_transforms:
                    for bone in obj.pose.bones:
                        if bone.name in bones_transforms[obj.name]:
                            bone.matrix_basis = (
                                bones_transforms[obj.name][bone.name]
                            )

    @contextmanager
    def maintained_modifiers(self, objects):
        """Maintain modifiers during context."""
        objects_modifiers = [
            [ModifierDescriptor(modifier) for modifier in obj.modifiers]
            for obj in objects
        ]
        try:
            yield
        finally:
            # Restor modifiers.
            for modifiers in objects_modifiers:
                for modifier in modifiers:
                    modifier.restor()
                # Restor modifiers order.
                #   NOTE (kaamaurice) This could be verry tricky if the
                #   upstream object hasn't the same modifiers count.
                #   So currently we reorder only non-override modifiers
                #   and if object has the same modifiers count.
                for modifier in modifiers:
                    obj = modifier.get_object()
                    if not obj or len(obj.modifiers) != len(modifiers):
                        break
                    if not modifier.is_override_data:
                        modifier.reorder()

    @contextmanager
    def maintained_constraints(self, objects):
        """Maintain constraints during context."""
        objects_constraints = []
        armature_constraints = []
        for obj in objects:
            objects_constraints.append(
                [
                    ConstraintDescriptor(constraint)
                    for constraint in obj.constraints
                ]
            )
            if obj.type == "ARMATURE":
                armature_constraints.append(
                    {
                        bone.name: [
                            ConstraintDescriptor(constraint)
                            for constraint in bone.constraints
                        ]
                        for bone in obj.pose.bones
                    }
                )
        try:
            yield
        finally:
            # Restor constraints.
            for constraints in objects_constraints:
                for constraint in constraints:
                    constraint.restor()
            for bones_constraints in armature_constraints:
                for bone_name, constraints in bones_constraints.items():
                    for constraint in constraints:
                        constraint.restor(bone_name=bone_name)

    @contextmanager
    def maintained_targets(self, objects):
        """Maintain constraints during context."""
        scene_objects = set(bpy.context.scene.objects) - set(objects)
        stored_targets = []
        for obj in scene_objects:
            # store constraints targets from object
            stored_targets += [
                (constraint, constraint.target.name, "target")
                for constraint in obj.constraints
                if getattr(constraint, "target", None) in objects
            ]
            # store modifiers targets from object
            for attr_name in ("target", "object", "object_from", "object_to"):
                stored_targets += [
                    (modifier, getattr(modifier, attr_name).name, attr_name)
                    for modifier in obj.modifiers
                    if getattr(modifier, attr_name, None) in objects
                ]
            # store constraints targets from bones in armature
            if obj.type == "ARMATURE":
                for bone in obj.pose.bones:
                    stored_targets += [
                        (constraint, constraint.target.name, "target")
                        for constraint in bone.constraints
                        if getattr(constraint, "target", None) in objects
                    ]
            # store texture mesh target from mesh object
            if obj.type == "MESH":
                if obj.data.texture_mesh in objects:
                    stored_targets.append(
                        (obj.data, obj.data.texture_mesh.name, "texture_mesh")
                    )
            # store driver variable targets from animation data
            if obj.animation_data:
                for driver in obj.animation_data.drivers:
                    for var in driver.driver.variables:
                        for target in var.targets:
                            if target.id in objects:
                                stored_targets.append(
                                    target, target.id.name, "id"
                                )
        try:
            yield
        finally:
            # Restor targets.
            for entity, target_name, attr_name in stored_targets:
                target = bpy.context.scene.objects.get(target_name)
                if target and hasattr(entity, attr_name):
                    setattr(entity, attr_name, target)

    @contextmanager
    def maintained_drivers(self, objects):
        """Maintain drivers during context."""
        objects_drivers = {}
        objects_copies = []
        for obj in objects:
            if obj.animation_data and len(obj.animation_data.drivers):
                obj_copy = obj.copy()
                obj_copy.name = f"{obj_copy.name}.copy"
                obj_copy.use_fake_user = True
                objects_copies.append(obj_copy)
                objects_drivers[obj.name] = [
                    driver
                    for driver in obj_copy.animation_data.drivers
                ]
        try:
            yield
        finally:
            # Restor drivers.
            for obj_name, drivers in objects_drivers.items():
                obj = bpy.context.scene.objects.get(obj_name)
                if not obj:
                    continue
                if not obj.animation_data:
                    obj.animation_data_create()
                for driver in drivers:
                    obj.animation_data.drivers.from_existing(src_driver=driver)
            # Clear copies.
            for obj_copy in objects_copies:
                obj_copy.use_fake_user = False
                bpy.data.objects.remove(obj_copy)

    @contextmanager
    def maintained_actions(self, objects):
        """Maintain action during context."""
        actions = {}
        # Store actions from objects.
        for obj in objects:
            if obj.animation_data and obj.animation_data.action:
                actions[obj.name] = obj.animation_data.action
                obj.animation_data.action.use_fake_user = True
        try:
            yield
        finally:
            # Restor actions.
            for obj_name, action in actions.items():
                obj = bpy.context.scene.objects.get(obj_name)
                if obj:
                    if obj.animation_data is None:
                        obj.animation_data_create()
                    obj.animation_data.action = action
            # Clear fake user.
            for action in actions.values():
                action.use_fake_user = False

    @contextmanager
    def maintained_local_data(self, objects, data_types):
        """Maintain local data during context."""
        local_data = {}
        # Store local data from mesh objects.
        for obj in objects:
            if (
                obj.type == "MESH"
                and not obj.data.library
                and not obj.data.override_library
            ):
                # TODO : check if obj.data has data_type
                local_copy = obj.data.copy()
                local_copy.name = f"{obj.data.name}.copy"
                local_copy.use_fake_user = True
                local_data[obj.name] = local_copy
        try:
            yield
        finally:
            # Transfert local data.
            for obj_name, data in local_data.items():
                obj = bpy.context.scene.objects.get(obj_name)
                if obj and obj.type == "MESH":

                    if obj.override_library:
                        if hasattr(obj.override_library, "destroy"):
                            obj.override_library.destroy()
                        else:
                            ref = obj.override_library.reference
                            obj.user_remap(ref)
                        obj = bpy.context.scene.objects.get(obj_name)
                    if obj.library:
                        obj = obj.make_local()
                        obj.data.make_local()

                    tmp = bpy.data.objects.new("tmp", data)
                    link_to_collection(tmp, bpy.context.scene.collection)
                    tmp.matrix_world = obj.matrix_world.copy()

                    deselect_all()
                    bpy.context.view_layer.objects.active = tmp
                    obj.select_set(True)
                    context = create_blender_context(active=tmp, selected=obj)

                    if data.unit_test_compare(mesh=obj.data) == "Same":
                        mapping = {
                            "vert_mapping": "TOPOLOGY",
                            "edge_mapping": "TOPOLOGY",
                            "loop_mapping": "TOPOLOGY",
                            "poly_mapping": "TOPOLOGY",
                        }
                    else:
                        mapping = {
                            "vert_mapping": "EDGE_NEAREST",
                            "edge_mapping": "POLY_NEAREST",
                            "loop_mapping": "NEAREST_POLYNOR",
                            "poly_mapping": "NEAREST",
                        }

                    for data_type in data_types:
                        bpy.ops.object.data_transfer(
                            context,
                            data_type=data_type,
                            layers_select_src="ALL",
                            layers_select_dst="NAME",
                            **mapping
                        )

                    bpy.data.objects.remove(tmp)
                    deselect_all()

            # Clear local data.
            for data in local_data.values():
                bpy.data.meshes.remove(data)


class Creator(LegacyCreator):
    """Base class for Creator plug-ins."""
    defaults = ['Main']
    color_tag = "NONE"

    def _use_selection(self, container):
        selected_objects = set(get_selection())
        # Get collection from selected objects.
        selected_collections = set()
        for collection in get_collections_by_objects(selected_objects):
            selected_collections.add(collection)
            selected_objects -= set(collection.all_objects)
        # Get collection from selected armature.
        selected_armatures = [
            obj
            for obj in selected_objects if obj.type == "ARMATURE"
        ]
        for armature in selected_armatures:
            for collection in get_collections_by_armature(armature):
                selected_collections.add(collection)
                selected_objects -= set(collection.all_objects)

        # Link Selected
        link_to_collection(selected_objects, container)
        link_to_collection(selected_collections, container)

        # Unlink from scene collection root if needed
        for obj in selected_objects:
            if obj in set(bpy.context.scene.collection.objects):
                bpy.context.scene.collection.objects.unlink(obj)
        for collection in selected_collections:
            if collection in set(bpy.context.scene.collection.children):
                bpy.context.scene.collection.children.unlink(collection)

    def _process(self):
        # Get info from data and create name value.
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = asset_name(asset, subset)

        # Create the container.
        container = create_container(name, self.color_tag)
        if container is None:
            raise RuntimeError(f"This instance already exists: {name}")

        # Add custom property on the instance container with the data.
        self.data["task"] = legacy_io.Session.get("AVALON_TASK")
        imprint(container, self.data)

        # Add selected objects to container if useSelection is True.
        if (self.options or {}).get("useSelection"):
            self._use_selection(container)

        return container

    def process(self):
        """Run the creator on Blender main thread."""
        mti = MainThreadItem(self._process)
        execute_in_main_thread(mti)


class Loader(LoaderPlugin):
    """Base class for Loader plug-ins."""

    hosts = ["blender"]
    representations = []


class AssetLoader(LoaderPlugin):
    """A basic AssetLoader for Blender

    This will implement the basic logic for linking/appending assets
    into another Blender scene.

    The `update` method should be implemented by a sub-class, because
    it's different for different types (e.g. model, rig, animation,
    etc.).
    """
    update_mainterner = ContainerMaintainer

    def _get_container_from_collections(
        self, collections: List, famillies: Optional[List] = None
    ) -> Optional[bpy.types.Collection]:
        """Get valid container from loaded collections."""
        for collection in collections:
            metadata = collection.get(AVALON_PROPERTY)
            if (
                metadata
                and (not famillies or metadata.get("family") in famillies)
            ):
                return collection

    def _get_asset_group_container(
        self, container: dict
    ) -> Optional[Union[bpy.types.Object, bpy.types.Collection]]:
        """Get asset group from container dict."""
        object_name = container["objectName"]
        family = container.get("family")

        scene = bpy.context.scene
        asset_group = scene.objects.get(object_name)
        if asset_group and is_container(asset_group, family):
            return asset_group

        for collection in get_children_recursive(scene.collection):
            if collection.name == object_name:
                asset_group = collection
                break
        else:
            asset_group = bpy.data.collections.get(object_name)

        if asset_group and is_container(asset_group, family):
            return asset_group

    def _rename_with_namespace(
        self,
        asset_group: Union[bpy.types.Object, bpy.types.Collection],
        namespace: str
    ):
        """Rename all objects and child collections from asset_group and
        their dependencies with namespace prefix.
        """
        materials = set()
        objects_data = set()

        for obj in get_container_objects(asset_group):

            if obj is not asset_group:
                obj.name = f"{namespace}:{obj.name}"

            if obj.data and not obj.data.library and obj.data.users == 1:
                objects_data.add(obj.data)

            if obj.type == 'MESH':
                for material_slot in obj.material_slots:
                    mtl = material_slot.material
                    if mtl and not mtl.library and mtl.users == 1:
                        materials.add(material_slot.material)

            elif obj.type == 'ARMATURE':
                anim_data = obj.animation_data
                if anim_data:
                    action = anim_data.action
                    if action and not action.library and action.users == 1:
                        action.name = f"{namespace}:{anim_data.action.name}"

        for data in objects_data:
            data.name = f"{namespace}:{data.name}"

        for material in materials:
            material.name = f"{namespace}:{material.name}"

        if isinstance(asset_group, bpy.types.Collection):
            for child in set(get_children_recursive(asset_group)):
                child.name = f"{namespace}:{child.name}"

    def _load_library_collection(self, libpath: str) -> bpy.types.Collection:
        """Load library from libpath and return the valid collection."""
        # Load collections from libpath library.
        with bpy.data.libraries.load(
            libpath, link=True, relative=False
        ) as (data_from, data_to):
            data_to.collections = data_from.collections

        # Get the right asset container from imported collections.
        container = self._get_container_from_collections(
            data_to.collections, self.families
        )
        assert container, "No asset container found"

        return container

    def _load_fbx(self, libpath, asset_group):
        """Load fbx process."""

        current_objects = set(bpy.data.objects)

        bpy.ops.import_scene.fbx(filepath=libpath)

        objects = set(bpy.data.objects) - current_objects

        for obj in objects:
            for collection in obj.users_collection:
                collection.objects.unlink(obj)

        link_to_collection(objects, asset_group)

        orphans_purge()
        deselect_all()

    def _load_blend(self, libpath, asset_group):
        """Load blend process."""
        # Load collections from libpath library.
        library_collection = self._load_library_collection(libpath)

        # Create override for the library collection and this elements.
        if hasattr(library_collection, "override_hierarchy_create"):
            override = library_collection.override_hierarchy_create(
                bpy.context.scene, bpy.context.view_layer
            )
        else:
            # If override_hierarchy_create method is not implemented for older
            # Blender versions we need the following steps.
            link_to_collection(
                library_collection, bpy.context.scene.collection
            )
            override = library_collection.override_create(
                remap_local_usages=True
            )

            for child in get_children_recursive(override):
                child.override_create(remap_local_usages=True)

            for obj in set(override.all_objects):
                obj.override_create(remap_local_usages=True)

            # force remap to fix modifers, constaints and drivers targets.
            for obj in set(override.all_objects):
                obj.override_library.reference.user_remap(obj.id_data)

        # Since Blender 3.2 property is_system_override need to be False
        # for editable override library.
        if hasattr(override.override_library, "is_system_override"):
            for obj in set(override.all_objects):
                obj.override_library.is_system_override = False
            for child in set(override.children):
                child.override_library.is_system_override = False

        # Move objects and child collections from override to asset_group.
        link_to_collection(override.objects, asset_group)
        link_to_collection(override.children, asset_group)

        # Clear and purge useless datablocks.
        bpy.data.collections.remove(override)
        orphans_purge()

        # Clear selection.
        deselect_all()

    def _process(*args, **kwargs):
        """Must be implemented by a sub-class"""
        raise NotImplementedError("Must be implemented by a sub-class")

    def process_asset(
        self,
        context: dict,
        name: str,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> bpy.types.Collection:
        """
        Arguments:
            name: Use pre-defined name
            namespace: Use pre-defined namespace
            context: Full parenthood of representation to load
            options: Additional settings dictionary
        """
        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]

        if legacy_io.Session.get("AVALON_ASSET") == asset:
            group_name = asset_name(asset, subset)
            namespace = ""
        else:
            unique_number = get_unique_number(asset, subset)
            group_name = asset_name(asset, subset, unique_number)
            namespace = namespace or f"{asset}_{unique_number}"

        asset_group = bpy.data.collections.new(group_name)
        if hasattr(asset_group, "color_tag"):
            asset_group.color_tag = self.color_tag
        get_main_collection().children.link(asset_group)

        self._process(libpath, asset_group)

        if namespace:
            self._rename_with_namespace(asset_group, namespace)

        self._update_metadata(
            asset_group,
            context,
            name,
            namespace,
            asset_name(asset, subset),
            libpath
        )

        self[:] = list(asset_group.all_objects)
        return asset_group

    def load(
        self,
        context: dict,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Optional[bpy.types.Collection]:
        """Run the loader on Blender main thread"""
        mti = MainThreadItem(self._load, context, name, namespace, options)
        execute_in_main_thread(mti)

    def _load(
        self,
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
        assert Path(self.fname).exists(), f"{self.fname} doesn't exist."

        asset = context["asset"]["name"]
        subset = context["subset"]["name"]
        unique_number = get_unique_number(asset, subset)
        namespace = namespace or f"{asset}_{unique_number}"
        name = name or asset_name(asset, subset, unique_number)

        return self.process_asset(
            context=context,
            name=name,
            namespace=namespace,
            options=options,
        )

    def _is_updated(self, asset_group, libpath):
        """Check data before update. Return True if already updated."""

        assert Path(libpath).is_file(), (
            f"The library file doesn't exist: {libpath}"
        )
        assert Path(libpath).suffix.lower() in VALID_EXTENSIONS, (
            f"Unsupported library file: {libpath}"
        )

        asset_metadata = asset_group.get(AVALON_PROPERTY, {})

        group_libpath = asset_metadata.get("libpath", "")

        normalized_group_libpath = (
            Path(bpy.path.abspath(group_libpath)).resolve()
        )
        normalized_libpath = (
            Path(bpy.path.abspath(libpath)).resolve()
        )
        self.log.debug(
            f"normalized_group_libpath:\n  {normalized_group_libpath}\n"
            f"normalized_libpath:\n  {normalized_libpath}"
        )
        return normalized_group_libpath == normalized_libpath

    def _update_namespace(
        self, asset_group: Union[bpy.types.Collection, bpy.types.Object]
    ):
        """Update namespace from asset group name."""
        # Clear default blender numbering.
        split_name = asset_group.name.replace(".", "_").split("_")
        asset_number = next(
            (int(spl) for spl in split_name if spl.isdigit()), 0
        )
        split_name = [spl for spl in split_name if not spl.isdigit()]
        # Get asset and subset name from splited asset group name.
        if len(split_name) > 1:
            asset = "_".join(split_name[:-1])
            subset = split_name[-1]
        else:
            asset = split_name[0]
            subset = "Unknown"
        # Generate unique numbered namespace and asset group name.
        unique_number = get_unique_number(asset, subset, asset_number)
        namespace = f"{asset}_{unique_number}"
        asset_group_name = asset_name(asset, subset, unique_number)
        # update asset group name and metadate
        asset_group.name = asset_group_name
        asset_group[AVALON_PROPERTY]["namespace"] = namespace
        asset_group[AVALON_PROPERTY]["objectName"] = asset_group_name

    def _update_instancer(
        self, asset_group: bpy.types.Object
    ) -> Union[bpy.types.Collection, bpy.types.Object]:
        """Update instancer depending the context to match with the loader
        asset process.

        Arguments:
            asset_group: the instancer object.

        Returns:
            The updated object instancer or converted collection.
        """
        # Get instance collection and this metadata
        instance_collection = asset_group.instance_collection
        instance_metadata = instance_collection[AVALON_PROPERTY].to_dict()
        # Get current session task name and asset name
        session_task_name = legacy_io.Session.get("AVALON_TASK")
        session_asset_name = legacy_io.Session.get("AVALON_ASSET")

        # If instance collection is a model container and current session task
        # is not a downstream task of model task, we juste need to update the
        # instancer metadata and namespace because model loader can manage
        # instancers.
        if (
            is_container(instance_collection, "model")
            and session_task_name not in MODEL_DOWNSTREAM
        ):
            asset_group[AVALON_PROPERTY] = instance_metadata
            self._update_namespace(asset_group)

        # else if instance collection is container we need to convert instancer
        # object to a valid linked collection.
        elif is_container(instance_collection):
            # Keep collection name
            collection_name = asset_group.name

            # Deleting instancer.
            parent_collection = get_parent_collection(asset_group)
            asset_group.name = f"{asset_group.name}.removed"
            bpy.data.objects.remove(asset_group)
            # Creating collection for asset group.
            asset_group = bpy.data.collections.new(collection_name)
            if hasattr(asset_group, "color_tag"):
                asset_group.color_tag = self.color_tag
            asset_group[AVALON_PROPERTY] = instance_metadata
            asset_group[AVALON_PROPERTY]["libpath"] = ""  # force update
            # Link the asset group collection.
            parent_collection = parent_collection or get_main_collection()
            parent_collection.children.link(asset_group)
            # Update namespace if needed.
            if session_asset_name != instance_metadata.get("asset_name"):
                self._update_namespace(asset_group)

        return asset_group

    def _update_process(
        self,
        container: Dict,
        representation: Dict
    ) -> Union[bpy.types.Collection, bpy.types.Object]:
        """Update the loaded asset.

        This will remove all objects of the current collection, load the new
        ones and add them to the collection.
        """
        object_name = container["objectName"]
        asset_group = self._get_asset_group_container(container)
        libpath = get_representation_path(representation)

        self.log.info(
            "Container: %s\nRepresentation: %s",
            pformat(container, indent=2),
            pformat(representation, indent=2),
        )

        assert asset_group, f"The asset is not loaded: {object_name}"
        assert libpath, (
            f"No library file found for representation: {representation}"
        )

        # This part fix the update process with linked collections without the
        # OpenPYPE loader tool or api, as the Asset Browser from Blender 3.2
        if (
            isinstance(asset_group, bpy.types.Object)
            and asset_group.is_instancer
            and asset_group.instance_collection
        ):
            asset_group = self._update_instancer(asset_group)

        # check if asset group is updated with libpath, abort otherwise.
        if self._is_updated(asset_group, libpath):
            self.log.info("Asset already up to date, not updating...")
            return

        # Update the asset group with maintained contexts.
        with self.update_mainterner(asset_group):

            remove_container(asset_group, content_only=True)

            self._process(libpath, asset_group)

            # If asset had namespace, all this object will be renamed with
            # namespace as prefix.
            namespace = asset_group.get(AVALON_PROPERTY, {}).get("namespace")
            if namespace:
                self._rename_with_namespace(asset_group, namespace)

        # With maintained contextmanager functions some datablocks could
        # remain, so we do orphans purge one last time.
        orphans_purge()

        # Update override library operations from asset objects if available.
        for obj in get_container_objects(asset_group):
            if getattr(obj.override_library, "operations_update", None):
                obj.override_library.operations_update()

        # update metadata
        metadata_update(
            asset_group,
            {
                "libpath": libpath,
                "representation": str(representation["_id"]),
                "parent": str(representation["parent"]),
            }
        )

        return asset_group

    def _update_metadata(
        self,
        asset_group: Union[bpy.types.Collection, bpy.types.Object],
        context: dict,
        name: str,
        namespace: str,
        asset_name: str,
        libpath: str
    ):
        """Update the asset group metadata with the given arguments and some
        default values.
        """
        metadata_update(
            asset_group,
            {
                "schema": "openpype:container-2.0",
                "id": AVALON_CONTAINER_ID,
                "name": name,
                "namespace": namespace or "",
                "loader": str(self.__class__.__name__),
                "representation": str(context["representation"]["_id"]),
                "libpath": libpath,
                "asset_name": asset_name,
                "parent": str(context["representation"]["parent"]),
                "family": context["representation"]["context"]["family"],
                "objectName": asset_group.name
            }
        )

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""
        self._update_process(container, representation)

    def update(self, container: Dict, representation: Dict):
        """Run the update on Blender main thread"""
        mti = MainThreadItem(self.exec_update, container, representation)
        execute_in_main_thread(mti)

    def exec_remove(self, container: Dict) -> bool:
        """Remove the existing container from Blender scene"""
        return self._remove_container(container)

    def remove(self, container: Dict) -> bool:
        """Run the remove on Blender main thread"""
        mti = MainThreadItem(self.exec_remove, container)
        execute_in_main_thread(mti)

    def _remove_container(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container: Container to remove.

        Returns:
            Whether the container was deleted.
        """
        asset_group = self._get_asset_group_container(container)

        if not asset_group:
            return False

        remove_container(asset_group)
        orphans_purge()

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
                    ops_result = bpy.ops.object.modifier_move_up(
                        create_blender_context(active=obj, selected=obj),
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
