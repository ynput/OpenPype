from .. import api, pipeline
from . import lib
from ..vendor import Qt

import pyblish.api


def install():
    """Install Photoshop-specific functionality of avalon-core.

    This function is called automatically on calling `api.install(photoshop)`.
    """
    print("Installing Avalon Photoshop...")
    pyblish.api.register_host("photoshop")


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
    layers_meta = stub.get_layers_metadata()
    if layers_meta:
        for key, instance in layers_meta.items():
            if instance.get("schema") and \
                    "container" in instance.get("schema"):
                continue

            instance['uuid'] = key
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

    stub.remove_instance(instance.get("uuid"))
    layer = stub.get_layer(instance.get("uuid"))
    if layer:
        stub.rename_layer(instance.get("uuid"),
                          layer.name.replace(stub.PUBLISH_ICON, ''))


def _get_stub():
    """
        Handle pulling stub from PS to run operations on host
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


class Creator(api.Creator):
    """Creator plugin to create instances in Photoshop

    A LayerSet is created to support any number of layers in an instance. If
    the selection is used, these layers will be added to the LayerSet.
    """

    def process(self):
        # Photoshop can have multiple LayerSets with the same name, which does
        # not work with Avalon.
        msg = "Instance with name \"{}\" already exists.".format(self.name)
        stub = lib.stub()  # only after Photoshop is up
        for layer in stub.get_layers():
            if self.name.lower() == layer.Name.lower():
                msg = Qt.QtWidgets.QMessageBox()
                msg.setIcon(Qt.QtWidgets.QMessageBox.Warning)
                msg.setText(msg)
                msg.exec_()
                return False

        # Store selection because adding a group will change selection.
        with lib.maintained_selection():

            # Add selection to group.
            if (self.options or {}).get("useSelection"):
                group = stub.group_selected_layers(self.name)
            else:
                group = stub.create_group(self.name)

            stub.imprint(group, self.data)

        return group


def containerise(name,
                 namespace,
                 layer,
                 context,
                 loader=None,
                 suffix="_CON"):
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
        "id": pipeline.AVALON_CONTAINER_ID,
        "name": name,
        "namespace": namespace,
        "loader": str(loader),
        "representation": str(context["representation"]["_id"]),
        "members": [str(layer.id)]
    }
    stub = lib.stub()
    stub.imprint(layer, data)

    return layer
