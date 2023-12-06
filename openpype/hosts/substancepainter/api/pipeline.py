# -*- coding: utf-8 -*-
"""Pipeline tools for OpenPype Substance Painter integration."""
import os
import logging
from functools import partial

# Substance 3D Painter modules
import substance_painter.ui
import substance_painter.event
import substance_painter.project

import pyblish.api

from openpype.host import HostBase, IWorkfileHost, ILoadHost, IPublishHost
from openpype.settings import (
    get_current_project_settings,
    get_system_settings
)

from openpype.pipeline.template_data import get_template_data_with_names
from openpype.pipeline import (
    register_creator_plugin_path,
    register_loader_plugin_path,
    AVALON_CONTAINER_ID,
    Anatomy
)
from openpype.lib import (
    StringTemplate,
    register_event_callback,
    emit_event,
)
from openpype.pipeline.load import any_outdated_containers
from openpype.hosts.substancepainter import SUBSTANCE_HOST_DIR

from . import lib

log = logging.getLogger("openpype.hosts.substance")

PLUGINS_DIR = os.path.join(SUBSTANCE_HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")

OPENPYPE_METADATA_KEY = "OpenPype"
OPENPYPE_METADATA_CONTAINERS_KEY = "containers"  # child key
OPENPYPE_METADATA_CONTEXT_KEY = "context"        # child key
OPENPYPE_METADATA_INSTANCES_KEY = "instances"    # child key


class SubstanceHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    name = "substancepainter"

    def __init__(self):
        super(SubstanceHost, self).__init__()
        self._has_been_setup = False
        self.menu = None
        self.callbacks = []
        self.shelves = []

    def install(self):
        pyblish.api.register_host("substancepainter")

        pyblish.api.register_plugin_path(PUBLISH_PATH)
        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)

        log.info("Installing callbacks ... ")
        # register_event_callback("init", on_init)
        self._register_callbacks()
        # register_event_callback("before.save", before_save)
        # register_event_callback("save", on_save)
        register_event_callback("open", on_open)
        # register_event_callback("new", on_new)

        log.info("Installing menu ... ")
        self._install_menu()

        project_settings = get_current_project_settings()
        self._install_shelves(project_settings)

        self._has_been_setup = True

    def uninstall(self):
        self._uninstall_shelves()
        self._uninstall_menu()
        self._deregister_callbacks()

    def workfile_has_unsaved_changes(self):

        if not substance_painter.project.is_open():
            return False

        return substance_painter.project.needs_saving()

    def get_workfile_extensions(self):
        return [".spp", ".toc"]

    def save_workfile(self, dst_path=None):

        if not substance_painter.project.is_open():
            return False

        if not dst_path:
            dst_path = self.get_current_workfile()

        full_save_mode = substance_painter.project.ProjectSaveMode.Full
        substance_painter.project.save_as(dst_path, full_save_mode)

        return dst_path

    def open_workfile(self, filepath):

        if not os.path.exists(filepath):
            raise RuntimeError("File does not exist: {}".format(filepath))

        # We must first explicitly close current project before opening another
        if substance_painter.project.is_open():
            substance_painter.project.close()

        substance_painter.project.open(filepath)
        return filepath

    def get_current_workfile(self):
        if not substance_painter.project.is_open():
            return None

        filepath = substance_painter.project.file_path()
        if filepath and filepath.endswith(".spt"):
            # When currently in a Substance Painter template assume our
            # scene isn't saved. This can be the case directly after doing
            # "New project", the path will then be the template used. This
            # avoids Workfiles tool trying to save as .spt extension if the
            # file hasn't been saved before.
            return

        return filepath

    def get_containers(self):

        if not substance_painter.project.is_open():
            return

        metadata = substance_painter.project.Metadata(OPENPYPE_METADATA_KEY)
        containers = metadata.get(OPENPYPE_METADATA_CONTAINERS_KEY)
        if containers:
            for key, container in containers.items():
                container["objectName"] = key
                yield container

    def update_context_data(self, data, changes):

        if not substance_painter.project.is_open():
            return

        metadata = substance_painter.project.Metadata(OPENPYPE_METADATA_KEY)
        metadata.set(OPENPYPE_METADATA_CONTEXT_KEY, data)

    def get_context_data(self):

        if not substance_painter.project.is_open():
            return

        metadata = substance_painter.project.Metadata(OPENPYPE_METADATA_KEY)
        return metadata.get(OPENPYPE_METADATA_CONTEXT_KEY) or {}

    def _install_menu(self):
        from PySide2 import QtWidgets
        from openpype.tools.utils import host_tools

        parent = substance_painter.ui.get_main_window()

        tab_menu_label = os.environ.get("AVALON_LABEL") or "AYON"
        menu = QtWidgets.QMenu(tab_menu_label)

        action = menu.addAction("Create...")
        action.triggered.connect(
            lambda: host_tools.show_publisher(parent=parent,
                                              tab="create")
        )

        action = menu.addAction("Load...")
        action.triggered.connect(
            lambda: host_tools.show_loader(parent=parent, use_context=True)
        )

        action = menu.addAction("Publish...")
        action.triggered.connect(
            lambda: host_tools.show_publisher(parent=parent,
                                              tab="publish")
        )

        action = menu.addAction("Manage...")
        action.triggered.connect(
            lambda: host_tools.show_scene_inventory(parent=parent)
        )

        action = menu.addAction("Library...")
        action.triggered.connect(
            lambda: host_tools.show_library_loader(parent=parent)
        )

        menu.addSeparator()
        action = menu.addAction("Work Files...")
        action.triggered.connect(
            lambda: host_tools.show_workfiles(parent=parent)
        )

        substance_painter.ui.add_menu(menu)

        def on_menu_destroyed():
            self.menu = None

        menu.destroyed.connect(on_menu_destroyed)

        self.menu = menu

    def _uninstall_menu(self):
        if self.menu:
            self.menu.destroy()
            self.menu = None

    def _register_callbacks(self):
        # Prepare emit event callbacks
        open_callback = partial(emit_event, "open")

        # Connect to the Substance Painter events
        dispatcher = substance_painter.event.DISPATCHER
        for event, callback in [
            (substance_painter.event.ProjectOpened, open_callback)
        ]:
            dispatcher.connect(event, callback)
            # Keep a reference so we can deregister if needed
            self.callbacks.append((event, callback))

    def _deregister_callbacks(self):
        for event, callback in self.callbacks:
            substance_painter.event.DISPATCHER.disconnect(event, callback)
        self.callbacks.clear()

    def _install_shelves(self, project_settings):

        shelves = project_settings["substancepainter"].get("shelves", {})
        if not shelves:
            return

        # Prepare formatting data if we detect any path which might have
        # template tokens like {asset} in there.
        formatting_data = {}
        has_formatting_entries = any("{" in path for path in shelves.values())
        if has_formatting_entries:
            project_name = self.get_current_project_name()
            asset_name = self.get_current_asset_name()
            task_name = self.get_current_asset_name()
            system_settings = get_system_settings()
            formatting_data = get_template_data_with_names(project_name,
                                                           asset_name,
                                                           task_name,
                                                           system_settings)
            anatomy = Anatomy(project_name)
            formatting_data["root"] = anatomy.roots

        for name, path in shelves.items():
            shelf_name = None

            # Allow formatting with anatomy for the paths
            if "{" in path:
                path = StringTemplate.format_template(path, formatting_data)

            try:
                shelf_name = lib.load_shelf(path, name=name)
            except ValueError as exc:
                print(f"Failed to load shelf -> {exc}")

            if shelf_name:
                self.shelves.append(shelf_name)

    def _uninstall_shelves(self):
        for shelf_name in self.shelves:
            substance_painter.resource.Shelves.remove(shelf_name)
        self.shelves.clear()


def on_open():
    log.info("Running callback on open..")

    if any_outdated_containers():
        from openpype.widgets import popup

        log.warning("Scene has outdated content.")

        # Get main window
        parent = substance_painter.ui.get_main_window()
        if parent is None:
            log.info("Skipping outdated content pop-up "
                     "because Substance window can't be found.")
        else:

            # Show outdated pop-up
            def _on_show_inventory():
                from openpype.tools.utils import host_tools
                host_tools.show_scene_inventory(parent=parent)

            dialog = popup.Popup(parent=parent)
            dialog.setWindowTitle("Substance scene has outdated content")
            dialog.setMessage("There are outdated containers in "
                              "your Substance scene.")
            dialog.on_clicked.connect(_on_show_inventory)
            dialog.show()


def imprint_container(container,
                      name,
                      namespace,
                      context,
                      loader):
    """Imprint a loaded container with metadata.

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        container (dict): The (substance metadata) dictionary to imprint into.
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        context (dict): Asset information
        loader (load.LoaderPlugin): loader instance used to produce container.

    Returns:
        None

    """

    data = [
        ("schema", "openpype:container-2.0"),
        ("id", AVALON_CONTAINER_ID),
        ("name", str(name)),
        ("namespace", str(namespace) if namespace else None),
        ("loader", str(loader.__class__.__name__)),
        ("representation", str(context["representation"]["_id"])),
    ]
    for key, value in data:
        container[key] = value


def set_container_metadata(object_name, container_data, update=False):
    """Helper method to directly set the data for a specific container

    Args:
        object_name (str): The unique object name identifier for the container
        container_data (dict): The data for the container.
            Note 'objectName' data is derived from `object_name` and key in
            `container_data` will be ignored.
        update (bool): Whether to only update the dict data.

    """
    # The objectName is derived from the key in the metadata so won't be stored
    # in the metadata in the container's data.
    container_data.pop("objectName", None)

    metadata = substance_painter.project.Metadata(OPENPYPE_METADATA_KEY)
    containers = metadata.get(OPENPYPE_METADATA_CONTAINERS_KEY) or {}
    if update:
        existing_data = containers.setdefault(object_name, {})
        existing_data.update(container_data)  # mutable dict, in-place update
    else:
        containers[object_name] = container_data
    metadata.set("containers", containers)


def remove_container_metadata(object_name):
    """Helper method to remove the data for a specific container"""
    metadata = substance_painter.project.Metadata(OPENPYPE_METADATA_KEY)
    containers = metadata.get(OPENPYPE_METADATA_CONTAINERS_KEY)
    if containers:
        containers.pop(object_name, None)
        metadata.set("containers", containers)


def set_instance(instance_id, instance_data, update=False):
    """Helper method to directly set the data for a specific container

    Args:
        instance_id (str): Unique identifier for the instance
        instance_data (dict): The instance data to store in the metaadata.
    """
    set_instances({instance_id: instance_data}, update=update)


def set_instances(instance_data_by_id, update=False):
    """Store data for multiple instances at the same time.

    This is more optimal than querying and setting them in the metadata one
    by one.
    """
    metadata = substance_painter.project.Metadata(OPENPYPE_METADATA_KEY)
    instances = metadata.get(OPENPYPE_METADATA_INSTANCES_KEY) or {}

    for instance_id, instance_data in instance_data_by_id.items():
        if update:
            existing_data = instances.get(instance_id, {})
            existing_data.update(instance_data)
        else:
            instances[instance_id] = instance_data

    metadata.set("instances", instances)


def remove_instance(instance_id):
    """Helper method to remove the data for a specific container"""
    metadata = substance_painter.project.Metadata(OPENPYPE_METADATA_KEY)
    instances = metadata.get(OPENPYPE_METADATA_INSTANCES_KEY) or {}
    instances.pop(instance_id, None)
    metadata.set("instances", instances)


def get_instances_by_id():
    """Return all instances stored in the project instances metadata"""
    if not substance_painter.project.is_open():
        return {}

    metadata = substance_painter.project.Metadata(OPENPYPE_METADATA_KEY)
    return metadata.get(OPENPYPE_METADATA_INSTANCES_KEY) or {}


def get_instances():
    """Return all instances stored in the project instances as a list"""
    return list(get_instances_by_id().values())
