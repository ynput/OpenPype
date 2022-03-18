import os
from Qt import QtWidgets

import pyblish.api
import avalon.api
from avalon import io

from openpype.api import Logger
from openpype.lib import register_event_callback
from openpype.pipeline import (
    LegacyCreator,
    register_loader_plugin_path,
    deregister_loader_plugin_path,
    AVALON_CONTAINER_ID,
)
import openpype.hosts.photoshop

from . import lib

log = Logger.get_logger(__name__)

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.photoshop.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


def check_inventory():
    if not lib.any_outdated():
        return

    host = avalon.api.registered_host()
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

    message_box = QtWidgets.QMessageBox()
    message_box.setIcon(QtWidgets.QMessageBox.Warning)
    msg = "There are outdated containers in the scene."
    message_box.setText(msg)
    message_box.exec_()


def on_application_launch():
    check_inventory()


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle layer visibility on instance toggles."""
    instance[0].Visible = new_value


def install():
    """Install Photoshop-specific functionality of avalon-core.

    This function is called automatically on calling `api.install(photoshop)`.
    """
    log.info("Installing OpenPype Photoshop...")
    pyblish.api.register_host("photoshop")

    pyblish.api.register_plugin_path(PUBLISH_PATH)
    register_loader_plugin_path(LOAD_PATH)
    avalon.api.register_plugin_path(LegacyCreator, CREATE_PATH)
    log.info(PUBLISH_PATH)

    pyblish.api.register_callback(
        "instanceToggled", on_pyblish_instance_toggled
    )

    register_event_callback("application.launched", on_application_launch)


def uninstall():
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    deregister_loader_plugin_path(LOAD_PATH)
    avalon.api.deregister_plugin_path(LegacyCreator, CREATE_PATH)


def ls():
    """Yields containers from active Photoshop document

    This is the host-equivalent of api.ls(), but instead of listing
    assets on disk, it lists assets already loaded in Photoshop; once loaded
    they are called 'containers'

    Yields:
        dict: container

    """
    try:
        stub = lib.stub()  # only after Photoshop is up
    except lib.ConnectionNotEstablishedYet:
        print("Not connected yet, ignoring")
        return

    if not stub.get_active_document_name():
        return

    layers_meta = stub.get_layers_metadata()  # minimalize calls to PS
    for layer in stub.get_layers():
        data = stub.read(layer, layers_meta)

        # Skip non-tagged layers.
        if not data:
            continue

        # Filter to only containers.
        if "container" not in data["id"]:
            continue

        # Append transient data
        data["objectName"] = layer.name.replace(stub.LOADED_ICON, '')
        data["layer"] = layer

        yield data


def list_instances():
    """List all created instances to publish from current workfile.

    Pulls from File > File Info

    For SubsetManager

    Returns:
        (list) of dictionaries matching instances format
    """
    stub = _get_stub()

    if not stub:
        return []

    instances = []
    layers_meta = stub.get_layers_metadata()
    if layers_meta:
        for key, instance in layers_meta.items():
            schema = instance.get("schema")
            if schema and "container" in schema:
                continue

            instance['uuid'] = key
            instances.append(instance)

    return instances


def remove_instance(instance):
    """Remove instance from current workfile metadata.

    Updates metadata of current file in File > File Info and removes
    icon highlight on group layer.

    For SubsetManager

    Args:
        instance (dict): instance representation from subsetmanager model
    """
    stub = _get_stub()

    if not stub:
        return

    stub.remove_instance(instance.get("uuid"))
    layer = stub.get_layer(instance.get("uuid"))
    if layer:
        stub.rename_layer(instance.get("uuid"),
                          layer.name.replace(stub.PUBLISH_ICON, ''))


def _get_stub():
    """Handle pulling stub from PS to run operations on host

    Returns:
        (PhotoshopServerStub) or None
    """
    try:
        stub = lib.stub()  # only after Photoshop is up
    except lib.ConnectionNotEstablishedYet:
        print("Not connected yet, ignoring")
        return

    if not stub.get_active_document_name():
        return

    return stub


def containerise(
    name, namespace, layer, context, loader=None, suffix="_CON"
):
    """Imprint layer with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        layer (PSItem): Layer to containerise
        context (dict): Asset information
        loader (str, optional): Name of loader used to produce this container.
        suffix (str, optional): Suffix of container, defaults to `_CON`.

    Returns:
        container (str): Name of container assembly
    """
    layer.name = name + suffix

    data = {
        "schema": "openpype:container-2.0",
        "id": AVALON_CONTAINER_ID,
        "name": name,
        "namespace": namespace,
        "loader": str(loader),
        "representation": str(context["representation"]["_id"]),
        "members": [str(layer.id)]
    }
    stub = lib.stub()
    stub.imprint(layer, data)

    return layer
