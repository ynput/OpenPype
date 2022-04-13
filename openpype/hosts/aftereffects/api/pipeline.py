import os
import sys

from Qt import QtWidgets

import pyblish.api
from avalon import io

from openpype import lib
from openpype.api import Logger
from openpype.pipeline import (
    register_loader_plugin_path,
    register_creator_plugin_path,
    deregister_loader_plugin_path,
    deregister_creator_plugin_path,
    AVALON_CONTAINER_ID,
)
import openpype.hosts.aftereffects
from openpype.lib import register_event_callback

from .launch_logic import get_stub

log = Logger.get_logger(__name__)


HOST_DIR = os.path.dirname(
    os.path.abspath(openpype.hosts.aftereffects.__file__)
)
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")


def install():
    print("Installing Pype config...")

    pyblish.api.register_host("aftereffects")
    pyblish.api.register_plugin_path(PUBLISH_PATH)

    register_loader_plugin_path(LOAD_PATH)
    register_creator_plugin_path(CREATE_PATH)
    log.info(PUBLISH_PATH)

    pyblish.api.register_callback(
        "instanceToggled", on_pyblish_instance_toggled
    )

    register_event_callback("application.launched", application_launch)


def uninstall():
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    deregister_loader_plugin_path(LOAD_PATH)
    deregister_creator_plugin_path(CREATE_PATH)


def application_launch():
    """Triggered after start of app"""
    check_inventory()


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle layer visibility on instance toggles."""
    instance[0].Visible = new_value


def get_asset_settings():
    """Get settings on current asset from database.

    Returns:
        dict: Scene data.

    """
    asset_data = lib.get_asset()["data"]
    fps = asset_data.get("fps")
    frame_start = asset_data.get("frameStart")
    frame_end = asset_data.get("frameEnd")
    handle_start = asset_data.get("handleStart")
    handle_end = asset_data.get("handleEnd")
    resolution_width = asset_data.get("resolutionWidth")
    resolution_height = asset_data.get("resolutionHeight")
    duration = (frame_end - frame_start + 1) + handle_start + handle_end

    return {
        "fps": fps,
        "frameStart": frame_start,
        "frameEnd": frame_end,
        "handleStart": handle_start,
        "handleEnd": handle_end,
        "resolutionWidth": resolution_width,
        "resolutionHeight": resolution_height,
        "duration": duration
    }


def ls():
    """Yields containers from active AfterEffects document.

    This is the host-equivalent of api.ls(), but instead of listing
    assets on disk, it lists assets already loaded in AE; once loaded
    they are called 'containers'. Used in Manage tool.

    Containers could be on multiple levels, single images/videos/was as a
    FootageItem, or multiple items - backgrounds (folder with automatically
    created composition and all imported layers).

    Yields:
        dict: container

    """
    try:
        stub = get_stub()  # only after AfterEffects is up
    except lib.ConnectionNotEstablishedYet:
        print("Not connected yet, ignoring")
        return

    layers_meta = stub.get_metadata()
    for item in stub.get_items(comps=True,
                               folders=True,
                               footages=True):
        data = stub.read(item, layers_meta)
        # Skip non-tagged layers.
        if not data:
            continue

        # Filter to only containers.
        if "container" not in data["id"]:
            continue

        # Append transient data
        data["objectName"] = item.name.replace(stub.LOADED_ICON, '')
        data["layer"] = item
        yield data


def check_inventory():
    """Checks loaded containers if they are of highest version"""
    if not lib.any_outdated():
        return

    host = pyblish.api.registered_host()
    outdated_containers = []
    for container in host.ls():
        representation = container['representation']
        representation_doc = io.find_one(
            {
                "_id": io.ObjectId(representation),
                "type": "representation"
            },
            projection={"parent": True}
        )
        if representation_doc and not lib.is_latest(representation_doc):
            outdated_containers.append(container)

    # Warn about outdated containers.
    print("Starting new QApplication..")
    _app = QtWidgets.QApplication(sys.argv)

    message_box = QtWidgets.QMessageBox()
    message_box.setIcon(QtWidgets.QMessageBox.Warning)
    msg = "There are outdated containers in the scene."
    message_box.setText(msg)
    message_box.exec_()


def containerise(name,
                 namespace,
                 comp,
                 context,
                 loader=None,
                 suffix="_CON"):
    """
    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Creates dictionary payloads that gets saved into file metadata. Each
    container contains of who loaded (loader) and members (single or multiple
    in case of background).

    Arguments:
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        comp (AEItem): Composition to containerise
        context (dict): Asset information
        loader (str, optional): Name of loader used to produce this container.
        suffix (str, optional): Suffix of container, defaults to `_CON`.

    Returns:
        container (str): Name of container assembly
    """
    data = {
        "schema": "openpype:container-2.0",
        "id": AVALON_CONTAINER_ID,
        "name": name,
        "namespace": namespace,
        "loader": str(loader),
        "representation": str(context["representation"]["_id"]),
        "members": comp.members or [comp.id]
    }

    stub = get_stub()
    stub.imprint(comp.id, data)

    return comp


# created instances section
def list_instances():
    """
        List all created instances from current workfile which
        will be published.

        Pulls from File > File Info

        For SubsetManager

        Returns:
            (list) of dictionaries matching instances format
    """
    stub = _get_stub()
    if not stub:
        return []

    instances = []
    layers_meta = stub.get_metadata()

    for instance in layers_meta:
        if instance.get("id") == "pyblish.avalon.instance":
            instances.append(instance)
    return instances


def remove_instance(instance):
    """
        Remove instance from current workfile metadata.

        Updates metadata of current file in File > File Info and removes
        icon highlight on group layer.

        For SubsetManager

        Args:
            instance (dict): instance representation from subsetmanager model
    """
    stub = _get_stub()

    if not stub:
        return

    inst_id = instance.get("instance_id") or instance.get("uuid")  # legacy
    if not inst_id:
        log.warning("No instance identifier for {}".format(instance))
        return

    stub.remove_instance(inst_id)

    if instance.get("members"):
        item = stub.get_item(instance["members"][0])
        if item:
            stub.rename_item(item.id,
                             item.name.replace(stub.PUBLISH_ICON, ''))


# new publisher section
def get_context_data():
    meta = _get_stub().get_metadata()
    for item in meta:
        if item.get("id") == "publish_context":
            item.pop("id")
            return item

    return {}


def update_context_data(data, changes):
    item = data
    item["id"] = "publish_context"
    _get_stub().imprint(item["id"], item)


def get_context_title():
    """Returns title for Creator window"""
    import avalon.api

    project_name = avalon.api.Session["AVALON_PROJECT"]
    asset_name = avalon.api.Session["AVALON_ASSET"]
    task_name = avalon.api.Session["AVALON_TASK"]
    return "{}/{}/{}".format(project_name, asset_name, task_name)


def _get_stub():
    """
        Handle pulling stub from PS to run operations on host
    Returns:
        (AEServerStub) or None
    """
    try:
        stub = get_stub()  # only after Photoshop is up
    except lib.ConnectionNotEstablishedYet:
        print("Not connected yet, ignoring")
        return

    if not stub.get_active_document_name():
        return

    return stub
