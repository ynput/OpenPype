"""
Basic avalon integration
"""
import os
import contextlib
from collections import OrderedDict
from avalon import api as avalon
from avalon import schema
from pyblish import api as pyblish
from openpype.api import Logger
from openpype.pipeline import (
    LegacyCreator,
    register_loader_plugin_path,
    deregister_loader_plugin_path,
    AVALON_CONTAINER_ID,
)
from . import lib
from . import PLUGINS_DIR
from openpype.tools.utils import host_tools
log = Logger().get_logger(__name__)

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")

AVALON_CONTAINERS = ":AVALON_CONTAINERS"


def install():
    """Install resolve-specific functionality of avalon-core.

    This is where you install menus and register families, data
    and loaders into resolve.

    It is called automatically when installing via `api.install(resolve)`.

    See the Maya equivalent for inspiration on how to implement this.

    """
    from .. import get_resolve_module

    log.info("openpype.hosts.resolve installed")

    pyblish.register_host("resolve")
    pyblish.register_plugin_path(PUBLISH_PATH)
    log.info("Registering DaVinci Resovle plug-ins..")

    register_loader_plugin_path(LOAD_PATH)
    avalon.register_plugin_path(LegacyCreator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    # register callback for switching publishable
    pyblish.register_callback("instanceToggled", on_pyblish_instance_toggled)

    get_resolve_module()


def uninstall():
    """Uninstall all that was installed

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

    deregister_loader_plugin_path(LOAD_PATH)
    avalon.deregister_plugin_path(LegacyCreator, CREATE_PATH)
    avalon.deregister_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    # register callback for switching publishable
    pyblish.deregister_callback("instanceToggled", on_pyblish_instance_toggled)


def containerise(timeline_item,
                 name,
                 namespace,
                 context,
                 loader=None,
                 data=None):
    """Bundle Hiero's object into an assembly and imprint it with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        timeline_item (hiero.core.TrackItem): object to imprint as container
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        context (dict): Asset information
        loader (str, optional): Name of node used to produce this container.

    Returns:
        timeline_item (hiero.core.TrackItem): containerised object

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

    print("_ data_imprint: {}".format(data_imprint))
    lib.set_timeline_item_pype_tag(timeline_item, data_imprint)

    return timeline_item


def ls():
    """List available containers.

    This function is used by the Container Manager in Nuke. You'll
    need to implement a for-loop that then *yields* one Container at
    a time.

    See the `container.json` schema for details on how it should look,
    and the Maya equivalent, which is in `avalon.maya.pipeline`
    """

    # get all track items from current timeline
    all_timeline_items = lib.get_current_timeline_items(filter=False)

    for timeline_item_data in all_timeline_items:
        timeline_item = timeline_item_data["clip"]["item"]
        container = parse_container(timeline_item)
        if container:
            yield container


def parse_container(timeline_item, validate=True):
    """Return container data from timeline_item's openpype tag.

    Args:
        timeline_item (hiero.core.TrackItem): A containerised track item.
        validate (bool)[optional]: validating with avalon scheme

    Returns:
        dict: The container schema data for input containerized track item.

    """
    # convert tag metadata to normal keys names
    data = lib.get_timeline_item_pype_tag(timeline_item)

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

    container["objectName"] = timeline_item.GetName()

    # Store reference to the node object
    container["_timeline_item"] = timeline_item

    return container


def update_container(timeline_item, data=None):
    """Update container data to input timeline_item's openpype tag.

    Args:
        timeline_item (hiero.core.TrackItem): A containerised track item.
        data (dict)[optional]: dictionery with data to be updated

    Returns:
        bool: True if container was updated correctly

    """
    data = data or dict()

    container = lib.get_timeline_item_pype_tag(timeline_item)

    for _key, _value in container.items():
        try:
            container[_key] = data[_key]
        except KeyError:
            pass

    log.info("Updating container: `{}`".format(timeline_item))
    return bool(lib.set_timeline_item_pype_tag(timeline_item, container))


def launch_workfiles_app(*args):
    host_tools.show_workfiles()


def publish(parent):
    """Shorthand to publish from within host"""
    return host_tools.show_publish()


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

    from openpype.hosts.resolve import (
        set_publish_attribute
    )

    # Whether instances should be passthrough based on new value
    timeline_item = instance.data["item"]
    set_publish_attribute(timeline_item, new_value)


def remove_instance(instance):
    """Remove instance marker from track item."""
    instance_id = instance.get("uuid")

    selected_timeline_items = lib.get_current_timeline_items(
        filter=True, selecting_color=lib.publish_clip_color)

    found_ti = None
    for timeline_item_data in selected_timeline_items:
        timeline_item = timeline_item_data["clip"]["item"]

        # get openpype tag data
        tag_data = lib.get_timeline_item_pype_tag(timeline_item)
        _ti_id = tag_data.get("uuid")
        if _ti_id == instance_id:
            found_ti = timeline_item
            break

    if found_ti is None:
        return

    # removing instance by marker color
    print(f"Removing instance: {found_ti.GetName()}")
    found_ti.DeleteMarkersByColor(lib.pype_marker_color)


def list_instances():
    """List all created instances from current workfile."""
    listed_instances = []
    selected_timeline_items = lib.get_current_timeline_items(
        filter=True, selecting_color=lib.publish_clip_color)

    for timeline_item_data in selected_timeline_items:
        timeline_item = timeline_item_data["clip"]["item"]
        ti_name = timeline_item.GetName().split(".")[0]

        # get openpype tag data
        tag_data = lib.get_timeline_item_pype_tag(timeline_item)

        if tag_data:
            asset = tag_data.get("asset")
            subset = tag_data.get("subset")
            tag_data["label"] = f"{ti_name} [{asset}-{subset}]"
            listed_instances.append(tag_data)

    return listed_instances
