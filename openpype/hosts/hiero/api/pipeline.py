"""
Basic avalon integration
"""
from copy import deepcopy
import os
import contextlib
from collections import OrderedDict

from pyblish import api as pyblish
from openpype.lib import Logger
from openpype.pipeline import (
    schema,
    register_creator_plugin_path,
    register_loader_plugin_path,
    deregister_creator_plugin_path,
    deregister_loader_plugin_path,
    AVALON_CONTAINER_ID,
)
from openpype.tools.utils import host_tools
from . import lib, menu, events
import hiero

log = Logger.get_logger(__name__)

# plugin paths
API_DIR = os.path.dirname(os.path.abspath(__file__))
HOST_DIR = os.path.dirname(API_DIR)
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish").replace("\\", "/")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load").replace("\\", "/")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create").replace("\\", "/")

AVALON_CONTAINERS = ":AVALON_CONTAINERS"


def install():
    """Installing Hiero integration."""

    # adding all events
    events.register_events()

    log.info("Registering Hiero plug-ins..")
    pyblish.register_host("hiero")
    pyblish.register_plugin_path(PUBLISH_PATH)
    register_loader_plugin_path(LOAD_PATH)
    register_creator_plugin_path(CREATE_PATH)

    # register callback for switching publishable
    pyblish.register_callback("instanceToggled", on_pyblish_instance_toggled)

    # install menu
    menu.menu_install()
    menu.add_scripts_menu()

    # register hiero events
    events.register_hiero_events()


def uninstall():
    """
    Uninstalling Hiero integration for avalon

    """
    log.info("Deregistering Hiero plug-ins..")
    pyblish.deregister_host("hiero")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    deregister_loader_plugin_path(LOAD_PATH)
    deregister_creator_plugin_path(CREATE_PATH)

    # register callback for switching publishable
    pyblish.deregister_callback("instanceToggled", on_pyblish_instance_toggled)


def containerise(track_item,
                 name,
                 namespace,
                 context,
                 loader=None,
                 data=None):
    """Bundle Hiero's object into an assembly and imprint it with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        track_item (hiero.core.TrackItem): object to imprint as container
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        context (dict): Asset information
        loader (str, optional): Name of node used to produce this container.

    Returns:
        track_item (hiero.core.TrackItem): containerised object

    """

    data_imprint = OrderedDict({
        "schema": "openpype:container-2.0",
        "id": AVALON_CONTAINER_ID,
        "name": str(name),
        "namespace": str(namespace),
        "loader": str(loader),
        "representation": str(context["representation"]["_id"]),
    })

    if data:
        for k, v in data.items():
            data_imprint.update({k: v})

    log.debug("_ data_imprint: {}".format(data_imprint))
    lib.set_trackitem_openpype_tag(track_item, data_imprint)

    return track_item


def ls():
    """List available containers.

    This function is used by the Container Manager in Nuke. You'll
    need to implement a for-loop that then *yields* one Container at
    a time.

    See the `container.json` schema for details on how it should look,
    and the Maya equivalent, which is in `avalon.maya.pipeline`
    """

    # get all track items from current timeline
    all_items = lib.get_track_items()

    # append all video tracks
    for track in lib.get_current_sequence():
        if type(track) != hiero.core.VideoTrack:
            continue
        all_items.append(track)

    for item in all_items:
        container_data = parse_container(item)

        if isinstance(container_data, list):
            for _c in container_data:
                yield _c
        elif container_data:
            yield container_data


def parse_container(item, validate=True):
    """Return container data from track_item's pype tag.

    Args:
        item (hiero.core.TrackItem or hiero.core.VideoTrack):
            A containerised track item.
        validate (bool)[optional]: validating with avalon scheme

    Returns:
        dict: The container schema data for input containerized track item.

    """
    def data_to_container(item, data):
        if (
            not data
            or data.get("id") != "pyblish.avalon.container"
        ):
            return

        if validate and data and data.get("schema"):
            schema.validate(data)

        if not isinstance(data, dict):
            return

        # If not all required data return the empty container
        required = ['schema', 'id', 'name',
                    'namespace', 'loader', 'representation']

        if any(key not in data for key in required):
            return

        container = {key: data[key] for key in required}

        container["objectName"] = item.name()

        # Store reference to the node object
        container["_item"] = item

        return container

    # convert tag metadata to normal keys names
    if type(item) == hiero.core.VideoTrack:
        return_list = []
        _data = lib.get_track_openpype_data(item)

        if not _data:
            return
        # convert the data to list and validate them
        for _, obj_data in _data.items():
            container = data_to_container(item, obj_data)
            return_list.append(container)
        return return_list
    else:
        _data = lib.get_trackitem_openpype_data(item)
        return data_to_container(item, _data)


def _update_container_data(container, data):
    for key in container:
        try:
            container[key] = data[key]
        except KeyError:
            pass
    return container


def update_container(item, data=None):
    """Update container data to input track_item or track's
    openpype tag.

    Args:
        item (hiero.core.TrackItem or hiero.core.VideoTrack):
            A containerised track item.
        data (dict)[optional]: dictionery with data to be updated

    Returns:
        bool: True if container was updated correctly

    """

    data = data or {}
    data = deepcopy(data)

    if type(item) == hiero.core.VideoTrack:
        # form object data for test
        object_name = data["objectName"]

        # get all available containers
        containers = lib.get_track_openpype_data(item)
        container = lib.get_track_openpype_data(item, object_name)

        containers = deepcopy(containers)
        container = deepcopy(container)

        # update data in container
        updated_container = _update_container_data(container, data)
        # merge updated container back to containers
        containers.update({object_name: updated_container})

        return bool(lib.set_track_openpype_tag(item, containers))
    else:
        container = lib.get_trackitem_openpype_data(item)
        updated_container = _update_container_data(container, data)

        log.info("Updating container: `{}`".format(item.name()))
        return bool(lib.set_trackitem_openpype_tag(item, updated_container))


def launch_workfiles_app(*args):
    ''' Wrapping function for workfiles launcher '''
    from .lib import get_main_window

    main_window = get_main_window()
    # show workfile gui
    host_tools.show_workfiles(parent=main_window)


def publish(parent):
    """Shorthand to publish from within host"""
    return host_tools.show_publish(parent)


@contextlib.contextmanager
def maintained_selection():
    """Maintain selection during context

    Example:
        >>> with maintained_selection():
        ...     for track_item in track_items:
        ...         < do some stuff >
    """
    from .lib import (
        set_selected_track_items,
        get_selected_track_items
    )
    previous_selection = get_selected_track_items()
    reset_selection()
    try:
        # do the operation
        yield
    finally:
        reset_selection()
        set_selected_track_items(previous_selection)


def reset_selection():
    """Deselect all selected nodes
    """
    from .lib import set_selected_track_items
    set_selected_track_items([])


def reload_config():
    """Attempt to reload pipeline at run-time.

    CAUTION: This is primarily for development and debugging purposes.

    """
    import importlib

    for module in (
        "openpype.hosts.hiero.lib",
        "openpype.hosts.hiero.menu",
        "openpype.hosts.hiero.tags"
    ):
        log.info("Reloading module: {}...".format(module))
        try:
            module = importlib.import_module(module)
            import imp
            imp.reload(module)
        except Exception as e:
            log.warning("Cannot reload module: {}".format(e))
            importlib.reload(module)


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle node passthrough states on instance toggles."""

    log.info("instance toggle: {}, old_value: {}, new_value:{} ".format(
        instance, old_value, new_value))

    from openpype.hosts.hiero.api import (
        get_trackitem_openpype_tag,
        set_publish_attribute
    )

    # Whether instances should be passthrough based on new value
    track_item = instance.data["item"]
    tag = get_trackitem_openpype_tag(track_item)
    set_publish_attribute(tag, new_value)
