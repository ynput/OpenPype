"""
Basic avalon integration
"""
import os
import contextlib
from collections import OrderedDict

from avalon import schema
from pyblish import api as pyblish
from openpype.api import Logger
from openpype.pipeline import (
    register_creator_plugin_path,
    register_loader_plugin_path,
    deregister_creator_plugin_path,
    deregister_loader_plugin_path,
    AVALON_CONTAINER_ID,
)
from openpype.tools.utils import host_tools
from . import lib, menu, events

log = Logger().get_logger(__name__)

AVALON_CONFIG = os.getenv("AVALON_CONFIG", "pype")

# plugin paths
API_DIR = os.path.dirname(os.path.abspath(__file__))
HOST_DIR = os.path.dirname(API_DIR)
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish").replace("\\", "/")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load").replace("\\", "/")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create").replace("\\", "/")

AVALON_CONTAINERS = ":AVALON_CONTAINERS"


def install():
    """
    Installing Hiero integration for avalon

    Args:
        config (obj): avalon config module `pype` in our case, it is not
        used but required by avalon.api.install()

    """

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
    lib.set_track_item_pype_tag(track_item, data_imprint)

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
    all_track_items = lib.get_track_items()

    for track_item in all_track_items:
        container = parse_container(track_item)
        if container:
            yield container


def parse_container(track_item, validate=True):
    """Return container data from track_item's pype tag.

    Args:
        track_item (hiero.core.TrackItem): A containerised track item.
        validate (bool)[optional]: validating with avalon scheme

    Returns:
        dict: The container schema data for input containerized track item.

    """
    # convert tag metadata to normal keys names
    data = lib.get_track_item_pype_data(track_item)

    if validate and data and data.get("schema"):
        schema.validate(data)

    if not isinstance(data, dict):
        return

    # If not all required data return the empty container
    required = ['schema', 'id', 'name',
                'namespace', 'loader', 'representation']

    if not all(key in data for key in required):
        return

    container = {key: data[key] for key in required}

    container["objectName"] = track_item.name()

    # Store reference to the node object
    container["_track_item"] = track_item

    return container


def update_container(track_item, data=None):
    """Update container data to input track_item's pype tag.

    Args:
        track_item (hiero.core.TrackItem): A containerised track item.
        data (dict)[optional]: dictionery with data to be updated

    Returns:
        bool: True if container was updated correctly

    """
    data = data or dict()

    container = lib.get_track_item_pype_data(track_item)

    for _key, _value in container.items():
        try:
            container[_key] = data[_key]
        except KeyError:
            pass

    log.info("Updating container: `{}`".format(track_item.name()))
    return bool(lib.set_track_item_pype_tag(track_item, container))


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
        "avalon",
        "avalon.lib",
        "avalon.pipeline",
        "pyblish",
        "pypeapp",
        "{}.api".format(AVALON_CONFIG),
        "{}.hosts.hiero.lib".format(AVALON_CONFIG),
        "{}.hosts.hiero.menu".format(AVALON_CONFIG),
        "{}.hosts.hiero.tags".format(AVALON_CONFIG)
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
        get_track_item_pype_tag,
        set_publish_attribute
    )

    # Whether instances should be passthrough based on new value
    track_item = instance.data["item"]
    tag = get_track_item_pype_tag(track_item)
    set_publish_attribute(tag, new_value)
