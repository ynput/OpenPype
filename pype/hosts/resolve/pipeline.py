"""
Basic avalon integration
"""
import os
import contextlib
from collections import OrderedDict
from avalon.tools import workfiles
from avalon import api as avalon
from avalon import schema
from avalon.pipeline import AVALON_CONTAINER_ID
from pyblish import api as pyblish
import pype
from pype.api import Logger
from . import lib

log = Logger().get_logger(__name__, "resolve")

AVALON_CONFIG = os.environ["AVALON_CONFIG"]

LOAD_PATH = os.path.join(pype.PLUGINS_DIR, "resolve", "load")
CREATE_PATH = os.path.join(pype.PLUGINS_DIR, "resolve", "create")
INVENTORY_PATH = os.path.join(pype.PLUGINS_DIR, "resolve", "inventory")

PUBLISH_PATH = os.path.join(
    pype.PLUGINS_DIR, "resolve", "publish"
).replace("\\", "/")

AVALON_CONTAINERS = ":AVALON_CONTAINERS"
# IS_HEADLESS = not hasattr(cmds, "about") or cmds.about(batch=True)


def install():
    """Install resolve-specific functionality of avalon-core.

    This is where you install menus and register families, data
    and loaders into resolve.

    It is called automatically when installing via `api.install(resolve)`.

    See the Maya equivalent for inspiration on how to implement this.

    """
    from . import get_resolve_module

    # Disable all families except for the ones we explicitly want to see
    family_states = [
        "imagesequence",
        "mov",
        "clip"
    ]
    avalon.data["familiesStateDefault"] = False
    avalon.data["familiesStateToggled"] = family_states

    log.info("pype.hosts.resolve installed")

    pyblish.register_host("resolve")
    pyblish.register_plugin_path(PUBLISH_PATH)
    log.info("Registering DaVinci Resovle plug-ins..")

    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    # register callback for switching publishable
    pyblish.register_callback("instanceToggled", on_pyblish_instance_toggled)

    get_resolve_module()


def uninstall():
    """Uninstall all tha was installed

    This is where you undo everything that was done in `install()`.
    That means, removing menus, deregistering families and  data
    and everything. It should be as though `install()` was never run,
    because odds are calling this function means the user is interested
    in re-installing shortly afterwards. If, for example, he has been
    modifying the menu or registered families.

    """
    pyblish.deregister_host("resolve")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    log.info("Deregistering DaVinci Resovle plug-ins..")

    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.deregister_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

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
        "schema": "avalon-core:container-2.0",
        "id": AVALON_CONTAINER_ID,
        "name": str(name),
        "namespace": str(namespace),
        "loader": str(loader),
        "representation": str(context["representation"]["_id"]),
    })

    if data:
        for k, v in data.items():
            data_imprint.update({k: v})

    print("_ data_imprint: {}".format(data_imprint))
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
    all_track_items = lib.get_current_track_items(filter=False)

    for track_item_data in all_track_items:
        track_item = track_item_data["clip"]["item"]
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
    data = lib.get_track_item_pype_tag(track_item)

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

    container = lib.get_track_item_pype_tag(track_item)

    for _key, _value in container.items():
        try:
            container[_key] = data[_key]
        except KeyError:
            pass

    log.info("Updating container: `{}`".format(track_item))
    return bool(lib.set_track_item_pype_tag(track_item, container))


def launch_workfiles_app(*args):
    workdir = os.environ["AVALON_WORKDIR"]
    workfiles.show(workdir)


def publish(parent):
    """Shorthand to publish from within host"""
    from avalon.tools import publish
    return publish.show(parent)


@contextlib.contextmanager
def maintained_selection():
    """Maintain selection during context

    Example:
        >>> with maintained_selection():
        ...     node['selected'].setValue(True)
        >>> print(node['selected'].value())
        False
    """
    try:
        # do the operation
        yield
    finally:
        pass


def reset_selection():
    """Deselect all selected nodes
    """
    pass


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle node passthrough states on instance toggles."""

    log.info("instance toggle: {}, old_value: {}, new_value:{} ".format(
        instance, old_value, new_value))

    from pype.hosts.resolve import (
        set_publish_attribute
    )

    # Whether instances should be passthrough based on new value
    track_item = instance.data["item"]
    set_publish_attribute(track_item, new_value)
