from itertools import chain
import os
import re
import traceback
import importlib
import contextlib
from typing import Dict, Iterator, List, Union

import bpy
import addon_utils
from openpype.hosts.blender.api.properties import OpenpypeContainer
from openpype.hosts.blender.api.utils import BL_TYPE_DATAPATH
from openpype.lib import Logger
from openpype.pipeline import schema
from openpype.pipeline.constants import AVALON_CONTAINER_ID

from . import pipeline

log = Logger.get_logger(__name__)

def create_container(
    name: str, datablocks: List[bpy.types.ID]
) -> OpenpypeContainer:
    """Create OpenPype container in scene with name and relevant datablocks.

    Args:
        name (str): Container's name
        datablocks (List[bpy.types.ID]): Datablocks included by the datablock

    Returns:
        OpenpypeContainer: Created container
    """
    container = bpy.context.scene.openpype_containers.add()
    container.name = name
    for d in datablocks:
        d_ref = container.datablocks.add()
        d_ref.name = d.name
        d_ref.datapath = BL_TYPE_DATAPATH.get(type(d))

    return container


def parse_container(
    container: Union[bpy.types.Collection, bpy.types.Object],
    validate: bool = True
) -> Dict:
    """Return the container node's full container data.

    Args:
        container: A container node name.
        validate: turn the validation for the container on or off

    Returns:
        The container schema data for this container node.

    """

    data = read(container)

    # NOTE (kaamaurice): experimental for the internal Asset browser.
    if (
        not data
        and isinstance(container, bpy.types.Object)
        and container.is_instancer
        and container.instance_collection
    ):
        data.update(read(container.instance_collection))
        # Fix namespace if empty
        if not data.get("namespace"):
            match = re.match(r"(^[^_]+(_\d+)?).*", container.name)
            data["namespace"] = match.group(1) if match else container.name

    # Append transient data
    data["objectName"] = container.name

    if validate:
        schema.validate(data)

    return data


def ls() -> Iterator:
    """List containers from active Blender scene.

    This is the host-equivalent of api.ls(), but instead of listing assets on
    disk, it lists assets already loaded in Blender; once loaded they are
    called containers.
    """
    # Ensure containers
    scene_collections = bpy.context.scene.collection.children_recursive
    openpype_containers = bpy.context.scene.openpype_containers
    collections = lsattr("id", AVALON_CONTAINER_ID)
    children_to_skip = set(
        chain.from_iterable(
            [
                op_container["outliner_entity"].children_recursive
                for op_container in openpype_containers
                if isinstance(
                    op_container.get("outliner_entity"), bpy.types.Collection
                )
            ]
        )
    )

    # Create containers from outliner datablocks (e.g collection duplication)
    for collection in [
        e for e in collections if not openpype_containers.get(e.name)
    ]:
        if (
            collection in children_to_skip
            or collection not in scene_collections
        ):
            continue

        # Skip all collections of container
        children_to_skip.update(collection.children_recursive)
        if type(collection) is bpy.types.Collection:
            datablocks = [collection, *collection.children_recursive]
        elif type(collection) is bpy.types.Object:  # Instanced collection
            datablocks = [collection, collection.instance_collection]

        # Create container
        container = create_container(collection.name, datablocks)

        # Transfer container metadata and keep original outliner entity
        container[pipeline.AVALON_PROPERTY] = collection.get(
            pipeline.AVALON_PROPERTY
        )
        container["outliner_entity"] = collection

    # Clear containers when data has been deleted from the outliner
    for container in reversed(openpype_containers):
        # In case outliner entity removed, remove container
        if "outliner_entity" in container.keys() and not container.get(
            "outliner_entity"
        ):
            openpype_containers.remove(
                openpype_containers.find(container.name)
            )

    # Parse containers
    return [parse_container(container) for container in openpype_containers]
    

def load_scripts(paths):
    """Copy of `load_scripts` from Blender's implementation.

    It is possible that this function will be changed in future and usage will
    be based on Blender version.
    """
    import bpy_types

    loaded_modules = set()

    previous_classes = [
        cls
        for cls in bpy.types.bpy_struct.__subclasses__()
    ]

    def register_module_call(mod):
        register = getattr(mod, "register", None)
        if register:
            try:
                register()
            except:
                traceback.print_exc()
        else:
            print("\nWarning! '%s' has no register function, "
                  "this is now a requirement for registerable scripts" %
                  mod.__file__)

    def unregister_module_call(mod):
        unregister = getattr(mod, "unregister", None)
        if unregister:
            try:
                unregister()
            except:
                traceback.print_exc()

    def test_reload(mod):
        # reloading this causes internal errors
        # because the classes from this module are stored internally
        # possibly to refresh internal references too but for now, best not to.
        if mod == bpy_types:
            return mod

        try:
            return importlib.reload(mod)
        except:
            traceback.print_exc()

    def test_register(mod):
        if mod:
            register_module_call(mod)
            bpy.utils._global_loaded_modules.append(mod.__name__)

    from bpy_restrict_state import RestrictBlend

    with RestrictBlend():
        for base_path in paths:
            for path_subdir in bpy.utils._script_module_dirs:
                path = os.path.join(base_path, path_subdir)
                if not os.path.isdir(path):
                    continue

                bpy.utils._sys_path_ensure_prepend(path)

                # Only add to 'sys.modules' unless this is 'startup'.
                if path_subdir != "startup":
                    continue
                for mod in bpy.utils.modules_from_path(path, loaded_modules):
                    test_register(mod)

    addons_paths = []
    for base_path in paths:
        addons_path = os.path.join(base_path, "addons")
        if not os.path.exists(addons_path):
            continue
        addons_paths.append(addons_path)
        addons_module_path = os.path.join(addons_path, "modules")
        if os.path.exists(addons_module_path):
            bpy.utils._sys_path_ensure_prepend(addons_module_path)

    if addons_paths:
        # Fake addons
        origin_paths = addon_utils.paths

        def new_paths():
            paths = origin_paths() + addons_paths
            return paths

        addon_utils.paths = new_paths
        addon_utils.modules_refresh()

    # load template (if set)
    if any(bpy.utils.app_template_paths()):
        import bl_app_template_utils
        bl_app_template_utils.reset(reload_scripts=False)
        del bl_app_template_utils

    for cls in bpy.types.bpy_struct.__subclasses__():
        if cls in previous_classes:
            continue
        if not getattr(cls, "is_registered", False):
            continue
        for subcls in cls.__subclasses__():
            if not subcls.is_registered:
                print(
                    "Warning, unregistered class: %s(%s)" %
                    (subcls.__name__, cls.__name__)
                )


def append_user_scripts():
    user_scripts = os.environ.get("OPENPYPE_BLENDER_USER_SCRIPTS")
    if not user_scripts:
        return

    try:
        load_scripts(user_scripts.split(os.pathsep))
    except Exception:
        print("Couldn't load user scripts \"{}\"".format(user_scripts))
        traceback.print_exc()


def imprint(node: bpy.types.bpy_struct_meta_idprop, data: Dict):
    r"""Write `data` to `node` as userDefined attributes

    Arguments:
        node: Long name of node
        data: Dictionary of key/value pairs

    Example:
        >>> import bpy
        >>> def compute():
        ...   return 6
        ...
        >>> bpy.ops.mesh.primitive_cube_add()
        >>> cube = bpy.context.view_layer.objects.active
        >>> imprint(cube, {
        ...   "regularString": "myFamily",
        ...   "computedValue": lambda: compute()
        ... })
        ...
        >>> cube['avalon']['computedValue']
        6
    """

    imprint_data = dict()

    for key, value in data.items():
        if value is None:
            continue

        if callable(value):
            # Support values evaluated at imprint
            value = value()

        if not isinstance(value, (int, float, bool, str, list)):
            raise TypeError(f"Unsupported type: {type(value)}")

        imprint_data[key] = value

    pipeline.metadata_update(node, imprint_data)


def lsattr(attr: str,
           value: Union[str, int, bool, List, Dict, None] = None) -> List:
    r"""Return nodes matching `attr` and `value`

    Arguments:
        attr: Name of Blender property
        value: Value of attribute. If none
            is provided, return all nodes with this attribute.

    Example:
        >>> lsattr("id", "myId")
        ...   [bpy.data.objects["myNode"]
        >>> lsattr("id")
        ...   [bpy.data.objects["myNode"], bpy.data.objects["myOtherNode"]]

    Returns:
        list
    """

    return lsattrs({attr: value})


def lsattrs(attrs: Dict) -> List:
    r"""Return nodes with the given attribute(s).

    Arguments:
        attrs: Name and value pairs of expected matches

    Example:
        >>> lsattrs({"age": 5})  # Return nodes with an `age` of 5
        # Return nodes with both `age` and `color` of 5 and blue
        >>> lsattrs({"age": 5, "color": "blue"})

    Returns a list.

    """

    # For now return all objects, not filtered by scene/collection/view_layer.
    matches = set()
    for coll in dir(bpy.data):
        if not isinstance(
                getattr(bpy.data, coll),
                bpy.types.bpy_prop_collection,
        ):
            continue
        for node in getattr(bpy.data, coll):
            for attr, value in attrs.items():
                avalon_prop = node.get(pipeline.AVALON_PROPERTY)
                if not avalon_prop:
                    continue
                if (avalon_prop.get(attr)
                        and (value is None or avalon_prop.get(attr) == value)):
                    matches.add(node)
    return list(matches)


def read(node: bpy.types.bpy_struct_meta_idprop):
    """Return user-defined attributes from `node`"""

    data = node[pipeline.AVALON_PROPERTY]

    # Ignore hidden/internal data
    data = {
        key: value
        for key, value in data.items() if not key.startswith("_")
    }

    return data


def get_selection() -> List[bpy.types.Object]:
    """Return the selected objects from the current scene."""
    return [obj for obj in bpy.context.scene.objects if obj.select_get()]


@contextlib.contextmanager
def maintained_selection():
    r"""Maintain selection during context

    Example:
        >>> with maintained_selection():
        ...     # Modify selection
        ...     bpy.ops.object.select_all(action='DESELECT')
        >>> # Selection restored
    """

    previous_selection = get_selection()
    previous_active = bpy.context.view_layer.objects.active
    try:
        yield
    finally:
        # Clear the selection
        for node in get_selection():
            node.select_set(state=False)
        if previous_selection:
            for node in previous_selection:
                try:
                    node.select_set(state=True)
                except ReferenceError:
                    # This could happen if a selected node was deleted during
                    # the context.
                    log.exception("Failed to reselect")
                    continue
        try:
            bpy.context.view_layer.objects.active = previous_active
        except ReferenceError:
            # This could happen if the active node was deleted during the
            # context.
            log.exception("Failed to set active object.")


@contextlib.contextmanager
def maintained_time():
    """Maintain current frame during context."""
    current_time = bpy.context.scene.frame_current
    try:
        yield
    finally:
        bpy.context.scene.frame_current = current_time
