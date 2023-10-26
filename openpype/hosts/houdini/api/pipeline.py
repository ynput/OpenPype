# -*- coding: utf-8 -*-
"""Pipeline tools for OpenPype Houdini integration."""
import os
import sys
import logging
import contextlib

import hou  # noqa

from openpype.host import HostBase, IWorkfileHost, ILoadHost, IPublishHost

import pyblish.api

from openpype.pipeline import (
    register_creator_plugin_path,
    register_loader_plugin_path,
    register_inventory_action_path,
    AVALON_CONTAINER_ID,
)
from openpype.pipeline.load import any_outdated_containers
from openpype.hosts.houdini import HOUDINI_HOST_DIR
from openpype.hosts.houdini.api import lib, shelves, creator_node_shelves

from openpype.lib import (
    register_event_callback,
    emit_event,
)


log = logging.getLogger("openpype.hosts.houdini")

AVALON_CONTAINERS = "/obj/AVALON_CONTAINERS"
CONTEXT_CONTAINER = "/obj/OpenPypeContext"
IS_HEADLESS = not hasattr(hou, "ui")

PLUGINS_DIR = os.path.join(HOUDINI_HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


class HoudiniHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    name = "houdini"

    def __init__(self):
        super(HoudiniHost, self).__init__()
        self._op_events = {}
        self._has_been_setup = False

    def install(self):
        pyblish.api.register_host("houdini")
        pyblish.api.register_host("hython")
        pyblish.api.register_host("hpython")

        pyblish.api.register_plugin_path(PUBLISH_PATH)
        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)
        register_inventory_action_path(INVENTORY_PATH)

        log.info("Installing callbacks ... ")
        # register_event_callback("init", on_init)
        self._register_callbacks()
        register_event_callback("before.save", before_save)
        register_event_callback("save", on_save)
        register_event_callback("open", on_open)
        register_event_callback("new", on_new)

        pyblish.api.register_callback(
            "instanceToggled", on_pyblish_instance_toggled
        )

        self._has_been_setup = True
        # add houdini vendor packages
        hou_pythonpath = os.path.join(HOUDINI_HOST_DIR, "vendor")

        sys.path.append(hou_pythonpath)

        # Set asset settings for the empty scene directly after launch of
        # Houdini so it initializes into the correct scene FPS,
        # Frame Range, etc.
        # TODO: make sure this doesn't trigger when
        #       opening with last workfile.
        _set_context_settings()

        if not IS_HEADLESS:
            import hdefereval  # noqa, hdefereval is only available in ui mode
            # Defer generation of shelves due to issue on Windows where shelf
            # initialization during start up delays Houdini UI by minutes
            # making it extremely slow to launch.
            hdefereval.executeDeferred(shelves.generate_shelves)

        if not IS_HEADLESS:
            import hdefereval # noqa, hdefereval is only available in ui mode
            hdefereval.executeDeferred(creator_node_shelves.install)

    def workfile_has_unsaved_changes(self):
        return hou.hipFile.hasUnsavedChanges()

    def get_workfile_extensions(self):
        return [".hip", ".hiplc", ".hipnc"]

    def save_workfile(self, dst_path=None):
        # Force forwards slashes to avoid segfault
        if dst_path:
            dst_path = dst_path.replace("\\", "/")
        hou.hipFile.save(file_name=dst_path,
                         save_to_recent_files=True)
        return dst_path

    def open_workfile(self, filepath):
        # Force forwards slashes to avoid segfault
        filepath = filepath.replace("\\", "/")

        hou.hipFile.load(filepath,
                         suppress_save_prompt=True,
                         ignore_load_warnings=False)

        return filepath

    def get_current_workfile(self):
        current_filepath = hou.hipFile.path()
        if (os.path.basename(current_filepath) == "untitled.hip" and
                not os.path.exists(current_filepath)):
            # By default a new scene in houdini is saved in the current
            # working directory as "untitled.hip" so we need to capture
            # that and consider it 'not saved' when it's in that state.
            return None

        return current_filepath

    def get_containers(self):
        return ls()

    def _register_callbacks(self):
        for event in self._op_events.copy().values():
            if event is None:
                continue

            try:
                hou.hipFile.removeEventCallback(event)
            except RuntimeError as e:
                log.info(e)

        self._op_events[on_file_event_callback] = hou.hipFile.addEventCallback(
            on_file_event_callback
        )

    @staticmethod
    def create_context_node():
        """Helper for creating context holding node.

        Returns:
            hou.Node: context node

        """
        obj_network = hou.node("/obj")
        op_ctx = obj_network.createNode("subnet",
                                        node_name="OpenPypeContext",
                                        run_init_scripts=False,
                                        load_contents=False)

        op_ctx.moveToGoodPosition()
        op_ctx.setBuiltExplicitly(False)
        op_ctx.setCreatorState("OpenPype")
        op_ctx.setComment("OpenPype node to hold context metadata")
        op_ctx.setColor(hou.Color((0.081, 0.798, 0.810)))
        op_ctx.setDisplayFlag(False)
        op_ctx.hide(True)
        return op_ctx

    def update_context_data(self, data, changes):
        op_ctx = hou.node(CONTEXT_CONTAINER)
        if not op_ctx:
            op_ctx = self.create_context_node()

        lib.imprint(op_ctx, data)

    def get_context_data(self):
        op_ctx = hou.node(CONTEXT_CONTAINER)
        if not op_ctx:
            op_ctx = self.create_context_node()
        return lib.read(op_ctx)

    def save_file(self, dst_path=None):
        # Force forwards slashes to avoid segfault
        dst_path = dst_path.replace("\\", "/")

        hou.hipFile.save(file_name=dst_path,
                         save_to_recent_files=True)


def on_file_event_callback(event):
    if event == hou.hipFileEventType.AfterLoad:
        emit_event("open")
    elif event == hou.hipFileEventType.AfterSave:
        emit_event("save")
    elif event == hou.hipFileEventType.BeforeSave:
        emit_event("before.save")
    elif event == hou.hipFileEventType.AfterClear:
        emit_event("new")


def containerise(name,
                 namespace,
                 nodes,
                 context,
                 loader=None,
                 suffix=""):
    """Bundle `nodes` into a subnet and imprint it with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        nodes (list): Long names of nodes to containerise
        context (dict): Asset information
        loader (str, optional): Name of loader used to produce this container.
        suffix (str, optional): Suffix of container, defaults to `_CON`.

    Returns:
        container (str): Name of container assembly

    """

    # Ensure AVALON_CONTAINERS subnet exists
    subnet = hou.node(AVALON_CONTAINERS)
    if subnet is None:
        obj_network = hou.node("/obj")
        subnet = obj_network.createNode("subnet",
                                        node_name="AVALON_CONTAINERS")

    # Create proper container name
    container_name = "{}_{}".format(name, suffix or "CON")
    container = hou.node("/obj/{}".format(name))
    container.setName(container_name, unique_name=True)

    data = {
        "schema": "openpype:container-2.0",
        "id": AVALON_CONTAINER_ID,
        "name": name,
        "namespace": namespace,
        "loader": str(loader),
        "representation": str(context["representation"]["_id"]),
    }

    lib.imprint(container, data)

    # "Parent" the container under the container network
    hou.moveNodesTo([container], subnet)

    subnet.node(container_name).moveToGoodPosition()

    return container


def parse_container(container):
    """Return the container node's full container data.

    Args:
        container (hou.Node): A container node name.

    Returns:
        dict: The container schema data for this container node.

    """
    data = lib.read(container)

    # Backwards compatibility pre-schemas for containers
    data["schema"] = data.get("schema", "openpype:container-1.0")

    # Append transient data
    data["objectName"] = container.path()
    data["node"] = container

    return data


def ls():
    containers = []
    for identifier in (AVALON_CONTAINER_ID,
                       "pyblish.mindbender.container"):
        containers += lib.lsattr("id", identifier)

    for container in sorted(containers,
                            # Hou 19+ Python 3 hou.ObjNode are not
                            # sortable due to not supporting greater
                            # than comparisons
                            key=lambda node: node.path()):
        yield parse_container(container)


def before_save():
    return lib.validate_fps()


def on_save():

    log.info("Running callback on save..")

    # update houdini vars
    lib.update_houdini_vars_context_dialog()

    nodes = lib.get_id_required_nodes()
    for node, new_id in lib.generate_ids(nodes):
        lib.set_id(node, new_id, overwrite=False)


def _show_outdated_content_popup():
    # Get main window
    parent = lib.get_main_window()
    if parent is None:
        log.info("Skipping outdated content pop-up "
                 "because Houdini window can't be found.")
    else:
        from openpype.widgets import popup

        # Show outdated pop-up
        def _on_show_inventory():
            from openpype.tools.utils import host_tools
            host_tools.show_scene_inventory(parent=parent)

        dialog = popup.Popup(parent=parent)
        dialog.setWindowTitle("Houdini scene has outdated content")
        dialog.setMessage("There are outdated containers in "
                          "your Houdini scene.")
        dialog.on_clicked.connect(_on_show_inventory)
        dialog.show()


def on_open():

    if not hou.isUIAvailable():
        log.debug("Batch mode detected, ignoring `on_open` callbacks..")
        return

    log.info("Running callback on open..")

    # update houdini vars
    lib.update_houdini_vars_context_dialog()

    # Validate FPS after update_task_from_path to
    # ensure it is using correct FPS for the asset
    lib.validate_fps()

    if any_outdated_containers():
        parent = lib.get_main_window()
        if parent is None:
            # When opening Houdini with last workfile on launch the UI hasn't
            # initialized yet completely when the `on_open` callback triggers.
            # We defer the dialog popup to wait for the UI to become available.
            # We assume it will open because `hou.isUIAvailable()` returns True
            import hdefereval
            hdefereval.executeDeferred(_show_outdated_content_popup)
        else:
            _show_outdated_content_popup()

        log.warning("Scene has outdated content.")


def on_new():
    """Set project resolution and fps when create a new file"""

    if hou.hipFile.isLoadingHipFile():
        # This event also triggers when Houdini opens a file due to the
        # new event being registered to 'afterClear'. As such we can skip
        # 'new' logic if the user is opening a file anyway
        log.debug("Skipping on new callback due to scene being opened.")
        return

    log.info("Running callback on new..")
    _set_context_settings()

    # It seems that the current frame always gets reset to frame 1 on
    # new scene. So we enforce current frame to be at the start of the playbar
    # with execute deferred
    def _enforce_start_frame():
        start = hou.playbar.playbackRange()[0]
        hou.setFrame(start)

    if hou.isUIAvailable():
        import hdefereval
        hdefereval.executeDeferred(_enforce_start_frame)
    else:
        # Run without execute deferred when no UI is available because
        # without UI `hdefereval` is not available to import
        _enforce_start_frame()


def _set_context_settings():
    """Apply the project settings from the project definition

    Settings can be overwritten by an asset if the asset.data contains
    any information regarding those settings.

    Examples of settings:
        fps
        resolution
        renderer

    Returns:
        None
    """

    lib.reset_framerange()
    lib.update_houdini_vars_context()


def on_pyblish_instance_toggled(instance, new_value, old_value):
    """Toggle saver tool passthrough states on instance toggles."""
    @contextlib.contextmanager
    def main_take(no_update=True):
        """Enter root take during context"""
        original_take = hou.takes.currentTake()
        original_update_mode = hou.updateModeSetting()
        root = hou.takes.rootTake()
        has_changed = False
        try:
            if original_take != root:
                has_changed = True
                if no_update:
                    hou.setUpdateMode(hou.updateMode.Manual)
                hou.takes.setCurrentTake(root)
                yield
        finally:
            if has_changed:
                if no_update:
                    hou.setUpdateMode(original_update_mode)
                hou.takes.setCurrentTake(original_take)

    if not instance.data.get("_allowToggleBypass", True):
        return

    nodes = instance[:]
    if not nodes:
        return

    # Assume instance node is first node
    instance_node = nodes[0]

    if not hasattr(instance_node, "isBypassed"):
        # Likely not a node that can actually be bypassed
        log.debug("Can't bypass node: %s", instance_node.path())
        return

    if instance_node.isBypassed() != (not old_value):
        print("%s old bypass state didn't match old instance state, "
              "updating anyway.." % instance_node.path())

    try:
        # Go into the main take, because when in another take changing
        # the bypass state of a note cannot be done due to it being locked
        # by default.
        with main_take(no_update=True):
            instance_node.bypass(not new_value)
    except hou.PermissionError as exc:
        log.warning("%s - %s", instance_node.path(), exc)
