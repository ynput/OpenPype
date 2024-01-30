import os

from qtpy import QtWidgets

import pyblish.api

from openpype.lib import Logger, register_event_callback
from openpype.pipeline import (
    register_loader_plugin_path,
    register_creator_plugin_path,
    AVALON_CONTAINER_ID,
)
from openpype.hosts.aftereffects.api.workfile_template_builder import (
    AEPlaceholderLoadPlugin,
    AEPlaceholderCreatePlugin
)
from openpype.pipeline.load import any_outdated_containers
import openpype.hosts.aftereffects

from openpype.host import (
    HostBase,
    IWorkfileHost,
    ILoadHost,
    IPublishHost
)
from openpype.tools.utils import get_openpype_qt_app

from .launch_logic import get_stub
from .ws_stub import ConnectionNotEstablishedYet

log = Logger.get_logger(__name__)


HOST_DIR = os.path.dirname(
    os.path.abspath(openpype.hosts.aftereffects.__file__)
)
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")


class AfterEffectsHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    name = "aftereffects"

    def __init__(self):
        self._stub = None
        super(AfterEffectsHost, self).__init__()

    @property
    def stub(self):
        """
            Handle pulling stub from PS to run operations on host
        Returns:
            (AEServerStub) or None
        """
        if self._stub:
            return self._stub

        try:
            stub = get_stub()  # only after Photoshop is up
        except ConnectionNotEstablishedYet:
            print("Not connected yet, ignoring")
            return

        self._stub = stub
        return self._stub

    def install(self):
        print("Installing Pype config...")

        pyblish.api.register_host("aftereffects")
        pyblish.api.register_plugin_path(PUBLISH_PATH)

        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)

        register_event_callback("application.launched", application_launch)

    def get_workfile_extensions(self):
        return [".aep"]

    def save_workfile(self, dst_path=None):
        self.stub.saveAs(dst_path, True)

    def open_workfile(self, filepath):
        self.stub.open(filepath)

        return True

    def get_current_workfile(self):
        try:
            full_name = get_stub().get_active_document_full_name()
            if full_name and full_name != "null":
                return os.path.normpath(full_name).replace("\\", "/")
        except ValueError:
            print("Nothing opened")
            pass

        return None

    def get_containers(self):
        return ls()

    def get_context_data(self):
        meta = self.stub.get_metadata()
        for item in meta:
            if item.get("id") == "publish_context":
                item.pop("id")
                return item

        return {}

    def update_context_data(self, data, changes):
        item = data
        item["id"] = "publish_context"
        self.stub.imprint(item["id"], item)

    def get_workfile_build_placeholder_plugins(self):
        return [
            AEPlaceholderLoadPlugin,
            AEPlaceholderCreatePlugin
        ]

    # created instances section
    def list_instances(self):
        """List all created instances from current workfile which
        will be published.

        Pulls from File > File Info

        For SubsetManager

        Returns:
            (list) of dictionaries matching instances format
        """
        stub = self.stub
        if not stub:
            return []

        instances = []
        layers_meta = stub.get_metadata()

        for instance in layers_meta:
            if instance.get("id") == "pyblish.avalon.instance":
                instances.append(instance)
        return instances

    def remove_instance(self, instance):
        """Remove instance from current workfile metadata.

        Updates metadata of current file in File > File Info and removes
        icon highlight on group layer.

        For SubsetManager

        Args:
            instance (dict): instance representation from subsetmanager model
        """
        stub = self.stub

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


def application_launch():
    """Triggered after start of app"""
    check_inventory()


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
    except ConnectionNotEstablishedYet:
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
    if not any_outdated_containers():
        return

    # Warn about outdated containers.
    _app = get_openpype_qt_app()

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


def cache_and_get_instances(creator):
    """Cache instances in shared data.

    Storing all instances as a list as legacy instances might be still present.
    Args:
        creator (Creator): Plugin which would like to get instances from host.
    Returns:
        List[]: list of all instances stored in metadata
    """
    shared_key = "openpype.photoshop.instances"
    if shared_key not in creator.collection_shared_data:
        creator.collection_shared_data[shared_key] = \
            creator.host.list_instances()
    return creator.collection_shared_data[shared_key]
