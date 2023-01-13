import os
import sys
import traceback
from typing import Callable, Dict, List, Optional

import bpy
from openpype.hosts.blender.api import utils

from . import lib
from . import ops, properties, ui

import pyblish.api

from openpype.client import get_asset_by_name
from openpype.settings import get_project_settings
from openpype.pipeline import (
    legacy_io,
    register_loader_plugin_path,
    register_creator_plugin_path,
    register_inventory_action_path,
    deregister_loader_plugin_path,
    deregister_creator_plugin_path,
    deregister_inventory_action_path,
    AVALON_CONTAINER_ID,
)
from openpype.lib import (
    Logger,
    register_event_callback,
    emit_event
)
import openpype.hosts.blender
from openpype.settings import get_project_settings


HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.blender.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")
SCRIPTS_PATH = os.path.join(HOST_DIR, "scripts")

ORIGINAL_EXCEPTHOOK = sys.excepthook

# TODO refactor all imports to avoid this duplicate
AVALON_PROPERTY = utils.AVALON_PROPERTY

IS_HEADLESS = bpy.app.background

log = Logger.get_logger(__name__)


def pype_excepthook_handler(*args):
    traceback.print_exception(*args)


def install():
    """Install Blender configuration for Avalon."""
    sys.excepthook = pype_excepthook_handler

    pyblish.api.register_host("blender")
    pyblish.api.register_plugin_path(str(PUBLISH_PATH))

    register_loader_plugin_path(str(LOAD_PATH))
    register_creator_plugin_path(str(CREATE_PATH))
    register_inventory_action_path(str(INVENTORY_PATH))

    lib.append_user_scripts()

    register_event_callback("new", on_new)
    register_event_callback("open", on_open)

    _register_callbacks()
    _register_events()

    if not IS_HEADLESS:
        ops.register()
        properties.register()
        ui.register()


def uninstall():
    """Uninstall Blender configuration for Avalon."""
    sys.excepthook = ORIGINAL_EXCEPTHOOK

    pyblish.api.deregister_host("blender")
    pyblish.api.deregister_plugin_path(str(PUBLISH_PATH))

    deregister_loader_plugin_path(str(LOAD_PATH))
    deregister_creator_plugin_path(str(CREATE_PATH))
    deregister_inventory_action_path(str(INVENTORY_PATH))

    if not IS_HEADLESS:
        ops.unregister()
        properties.unregister()
        ui.unregister()


def show_message(title, message):
    from openpype.widgets.message_window import Window
    from .ops import BlenderApplication

    BlenderApplication.get_app()

    Window(
        parent=None,
        title=title,
        message=message,
        level="warning")


def message_window(title, message):
    from .ops import (
        MainThreadItem,
        execute_in_main_thread,
        _process_app_events
    )

    mti = MainThreadItem(show_message, title, message)
    execute_in_main_thread(mti)
    _process_app_events()


def set_start_end_frames():
    project_name = legacy_io.active_project()
    asset_name = legacy_io.Session["AVALON_ASSET"]
    asset_doc = get_asset_by_name(project_name, asset_name)

    scene = bpy.context.scene

    # Default scene settings
    frameStart = scene.frame_start
    frameEnd = scene.frame_end
    fps = scene.render.fps / scene.render.fps_base
    resolution_x = scene.render.resolution_x
    resolution_y = scene.render.resolution_y

    # Check if settings are set
    data = asset_doc.get("data")

    if not data:
        return

    if data.get("frameStart"):
        frameStart = data.get("frameStart")
    if data.get("frameEnd"):
        frameEnd = data.get("frameEnd")
    if data.get("fps"):
        fps = data.get("fps")
    if data.get("resolutionWidth"):
        resolution_x = data.get("resolutionWidth")
    if data.get("resolutionHeight"):
        resolution_y = data.get("resolutionHeight")

    scene.frame_start = frameStart
    scene.frame_end = frameEnd
    scene.render.fps = round(fps)
    scene.render.fps_base = round(fps) / fps
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y


def set_use_file_compression():
    project_name = legacy_io.active_project()
    project_setting = get_project_settings(project_name)
    compress = project_setting["blender"]["general"].get("compress")
    bpy.context.preferences.filepaths.use_file_compression = compress


def on_new():
    set_start_end_frames()
    set_use_file_compression()

    project = os.environ.get("AVALON_PROJECT")
    settings = get_project_settings(project)

    unit_scale_settings = settings.get("blender").get("unit_scale_settings")
    unit_scale_enabled = unit_scale_settings.get("enabled")
    if unit_scale_enabled:
        unit_scale = unit_scale_settings.get("base_file_unit_scale")
        bpy.context.scene.unit_settings.scale_length = unit_scale


def on_open():
    set_start_end_frames()
    set_use_file_compression()

    project = os.environ.get("AVALON_PROJECT")
    settings = get_project_settings(project)

    unit_scale_settings = settings.get("blender").get("unit_scale_settings")
    unit_scale_enabled = unit_scale_settings.get("enabled")
    apply_on_opening = unit_scale_settings.get("apply_on_opening")
    if unit_scale_enabled and apply_on_opening:
        unit_scale = unit_scale_settings.get("base_file_unit_scale")
        prev_unit_scale = bpy.context.scene.unit_settings.scale_length

        if unit_scale != prev_unit_scale:
            bpy.context.scene.unit_settings.scale_length = unit_scale

            message_window(
                "Base file unit scale changed",
                "Base file unit scale changed to match the project settings.")


@bpy.app.handlers.persistent
def _on_save_pre(*args):
    emit_event("before.save")


@bpy.app.handlers.persistent
def _on_save_post(*args):
    emit_event("save")


@bpy.app.handlers.persistent
def _on_load_post(*args):
    # Detect new file or opening an existing file
    if bpy.data.filepath:
        # Likely this was an open operation since it has a filepath
        emit_event("open")
    else:
        emit_event("new")

    ops.OpenFileCacher.post_load()


def _register_callbacks():
    """Register callbacks for certain events."""
    def _remove_handler(handlers: List, callback: Callable):
        """Remove the callback from the given handler list."""

        try:
            handlers.remove(callback)
        except ValueError:
            pass

    # TODO (jasper): implement on_init callback?

    # Be sure to remove existig ones first.
    _remove_handler(bpy.app.handlers.save_pre, _on_save_pre)
    _remove_handler(bpy.app.handlers.save_post, _on_save_post)
    _remove_handler(bpy.app.handlers.load_post, _on_load_post)

    bpy.app.handlers.save_pre.append(_on_save_pre)
    bpy.app.handlers.save_post.append(_on_save_post)
    bpy.app.handlers.load_post.append(_on_load_post)

    log.info("Installed event handler _on_save_pre...")
    log.info("Installed event handler _on_save_post...")
    log.info("Installed event handler _on_load_post...")


def _on_task_changed():
    """Callback for when the task in the context is changed."""

    # TODO (jasper): Blender has no concept of projects or workspace.
    # It would be nice to override 'bpy.ops.wm.open_mainfile' so it takes the
    # workdir as starting directory.  But I don't know if that is possible.
    # Another option would be to create a custom 'File Selector' and add the
    # `directory` attribute, so it opens in that directory (does it?).
    # https://docs.blender.org/api/blender2.8/bpy.types.Operator.html#calling-a-file-selector
    # https://docs.blender.org/api/blender2.8/bpy.types.WindowManager.html#bpy.types.WindowManager.fileselect_add
    workdir = legacy_io.Session["AVALON_WORKDIR"]
    log.debug("New working directory: %s", workdir)


def _register_events():
    """Install callbacks for specific events."""

    register_event_callback("taskChanged", _on_task_changed)
    log.info("Installed event callback for 'taskChanged'...")



def metadata_update(node: bpy.types.bpy_struct_meta_idprop, data: Dict):
    """Imprint the node with metadata.

    Existing metadata will be updated.
    """

    if not node.get(AVALON_PROPERTY):
        node[AVALON_PROPERTY] = dict()
    for key, value in data.items():
        node[AVALON_PROPERTY][key] = value


def containerise(name: str,
                 namespace: str,
                 nodes: List,
                 context: Dict,
                 loader: Optional[str] = None,
                 suffix: Optional[str] = "CON") -> bpy.types.Collection:
    """Bundle `nodes` into an assembly and imprint it with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        name: Name of resulting assembly
        namespace: Namespace under which to host container
        nodes: Long names of nodes to containerise
        context: Asset information
        loader: Name of loader used to produce this container.
        suffix: Suffix of container, defaults to `_CON`.

    Returns:
        The container assembly

    """

    node_name = f"{context['asset']['name']}_{name}"
    if namespace:
        node_name = f"{namespace}:{node_name}"
    if suffix:
        node_name = f"{node_name}_{suffix}"
    container = bpy.data.collections.new(name=node_name)
    # Link the children nodes
    for obj in nodes:
        container.objects.link(obj)

    data = {
        "schema": "openpype:container-2.0",
        "id": AVALON_CONTAINER_ID,
        "name": name,
        "namespace": namespace or '',
        "loader": str(loader),
        "representation": str(context["representation"]["_id"]),
    }

    metadata_update(container, data)

    return container


def containerise_existing(
        container: bpy.types.Collection,
        name: str,
        namespace: str,
        context: Dict,
        loader: Optional[str] = None,
        suffix: Optional[str] = "CON") -> bpy.types.Collection:
    """Imprint or update container with metadata.

    Arguments:
        name: Name of resulting assembly
        namespace: Namespace under which to host container
        context: Asset information
        loader: Name of loader used to produce this container.
        suffix: Suffix of container, defaults to `_CON`.

    Returns:
        The container assembly
    """

    node_name = container.name
    if suffix:
        node_name = f"{node_name}_{suffix}"
    container.name = node_name
    data = {
        "schema": "openpype:container-2.0",
        "id": AVALON_CONTAINER_ID,
        "name": name,
        "namespace": namespace or '',
        "loader": str(loader),
        "representation": str(context["representation"]["_id"]),
    }

    metadata_update(container, data)

    return container


def update_hierarchy(containers):
    """Hierarchical container support

    This is the function to support Scene Inventory to draw hierarchical
    view for containers.

    We need both parent and children to visualize the graph.

    """

    all_containers = set(lib.ls())  # lookup set

    for container in containers:
        # Find parent
        # FIXME (jasperge): re-evaluate this. How would it be possible
        # to 'nest' assets?  Collections can have several parents, for
        # now assume it has only 1 parent
        parent = [
            coll for coll in bpy.data.collections if container in coll.children
        ]
        for node in parent:
            if node in all_containers:
                container["parent"] = node
                break

        log.debug("Container: %s", container)

        yield container


def publish():
    """Shorthand to publish from within host."""

    return pyblish.util.publish()
