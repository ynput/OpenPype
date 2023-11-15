import os
import sys
import traceback
from typing import Callable, Dict, Iterator, List, Optional

import bpy

from . import lib
from . import ops

import pyblish.api

from openpype.host import (
    HostBase,
    IWorkfileHost,
    IPublishHost,
    ILoadHost
)
from openpype.client import get_asset_by_name
from openpype.pipeline import (
    schema,
    legacy_io,
    get_current_project_name,
    get_current_asset_name,
    register_loader_plugin_path,
    register_creator_plugin_path,
    deregister_loader_plugin_path,
    deregister_creator_plugin_path,
    AVALON_CONTAINER_ID,
)
from openpype.lib import (
    Logger,
    register_event_callback,
    emit_event
)
import openpype.hosts.blender
from openpype.settings import get_project_settings
from .workio import (
    open_file,
    save_file,
    current_file,
    has_unsaved_changes,
    file_extensions,
    work_root,
)


HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.blender.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")

ORIGINAL_EXCEPTHOOK = sys.excepthook

AVALON_INSTANCES = "AVALON_INSTANCES"
AVALON_CONTAINERS = "AVALON_CONTAINERS"
AVALON_PROPERTY = 'avalon'
IS_HEADLESS = bpy.app.background

log = Logger.get_logger(__name__)


class BlenderHost(HostBase, IWorkfileHost, IPublishHost, ILoadHost):
    name = "blender"

    def install(self):
        """Override install method from HostBase.
        Install Blender host functionality."""
        install()

    def get_containers(self) -> Iterator:
        """List containers from active Blender scene."""
        return ls()

    def get_workfile_extensions(self) -> List[str]:
        """Override get_workfile_extensions method from IWorkfileHost.
        Get workfile possible extensions.

        Returns:
            List[str]: Workfile extensions.
        """
        return file_extensions()

    def save_workfile(self, dst_path: str = None):
        """Override save_workfile method from IWorkfileHost.
        Save currently opened workfile.

        Args:
            dst_path (str): Where the current scene should be saved. Or use
                current path if `None` is passed.
        """
        save_file(dst_path if dst_path else bpy.data.filepath)

    def open_workfile(self, filepath: str):
        """Override open_workfile method from IWorkfileHost.
        Open workfile at specified filepath in the host.

        Args:
            filepath (str): Path to workfile.
        """
        open_file(filepath)

    def get_current_workfile(self) -> str:
        """Override get_current_workfile method from IWorkfileHost.
        Retrieve currently opened workfile path.

        Returns:
            str: Path to currently opened workfile.
        """
        return current_file()

    def workfile_has_unsaved_changes(self) -> bool:
        """Override wokfile_has_unsaved_changes method from IWorkfileHost.
        Returns True if opened workfile has no unsaved changes.

        Returns:
            bool: True if scene is saved and False if it has unsaved
                modifications.
        """
        return has_unsaved_changes()

    def work_root(self, session) -> str:
        """Override work_root method from IWorkfileHost.
        Modify workdir per host.

        Args:
            session (dict): Session context data.

        Returns:
            str: Path to new workdir.
        """
        return work_root(session)

    def get_context_data(self) -> dict:
        """Override abstract method from IPublishHost.
        Get global data related to creation-publishing from workfile.

        Returns:
            dict: Context data stored using 'update_context_data'.
        """
        property = bpy.context.scene.get(AVALON_PROPERTY)
        if property:
            return property.to_dict()
        return {}

    def update_context_data(self, data: dict, changes: dict):
        """Override abstract method from IPublishHost.
        Store global context data to workfile.

        Args:
            data (dict): New data as are.
            changes (dict): Only data that has been changed. Each value has
                tuple with '(<old>, <new>)' value.
        """
        bpy.context.scene[AVALON_PROPERTY] = data


def pype_excepthook_handler(*args):
    traceback.print_exception(*args)


def install():
    """Install Blender configuration for Avalon."""
    sys.excepthook = pype_excepthook_handler

    pyblish.api.register_host("blender")
    pyblish.api.register_plugin_path(str(PUBLISH_PATH))

    register_loader_plugin_path(str(LOAD_PATH))
    register_creator_plugin_path(str(CREATE_PATH))

    lib.append_user_scripts()
    lib.set_app_templates_path()

    register_event_callback("new", on_new)
    register_event_callback("open", on_open)

    _register_callbacks()
    _register_events()

    if not IS_HEADLESS:
        ops.register()


def uninstall():
    """Uninstall Blender configuration for Avalon."""
    sys.excepthook = ORIGINAL_EXCEPTHOOK

    pyblish.api.deregister_host("blender")
    pyblish.api.deregister_plugin_path(str(PUBLISH_PATH))

    deregister_loader_plugin_path(str(LOAD_PATH))
    deregister_creator_plugin_path(str(CREATE_PATH))

    if not IS_HEADLESS:
        ops.unregister()


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


def get_asset_data():
    project_name = get_current_project_name()
    asset_name = get_current_asset_name()
    asset_doc = get_asset_by_name(project_name, asset_name)

    return asset_doc.get("data")


def set_frame_range(data):
    scene = bpy.context.scene

    # Default scene settings
    frameStart = scene.frame_start
    frameEnd = scene.frame_end
    fps = scene.render.fps / scene.render.fps_base

    if not data:
        return

    if data.get("frameStart"):
        frameStart = data.get("frameStart")
    if data.get("frameEnd"):
        frameEnd = data.get("frameEnd")
    if data.get("fps"):
        fps = data.get("fps")

    scene.frame_start = frameStart
    scene.frame_end = frameEnd
    scene.render.fps = round(fps)
    scene.render.fps_base = round(fps) / fps


def set_resolution(data):
    scene = bpy.context.scene

    # Default scene settings
    resolution_x = scene.render.resolution_x
    resolution_y = scene.render.resolution_y

    if not data:
        return

    if data.get("resolutionWidth"):
        resolution_x = data.get("resolutionWidth")
    if data.get("resolutionHeight"):
        resolution_y = data.get("resolutionHeight")

    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y


def on_new():
    project = os.environ.get("AVALON_PROJECT")
    settings = get_project_settings(project).get("blender")

    set_resolution_startup = settings.get("set_resolution_startup")
    set_frames_startup = settings.get("set_frames_startup")

    data = get_asset_data()

    if set_resolution_startup:
        set_resolution(data)
    if set_frames_startup:
        set_frame_range(data)

    unit_scale_settings = settings.get("unit_scale_settings")
    unit_scale_enabled = unit_scale_settings.get("enabled")
    if unit_scale_enabled:
        unit_scale = unit_scale_settings.get("base_file_unit_scale")
        bpy.context.scene.unit_settings.scale_length = unit_scale


def on_open():
    project = os.environ.get("AVALON_PROJECT")
    settings = get_project_settings(project).get("blender")

    set_resolution_startup = settings.get("set_resolution_startup")
    set_frames_startup = settings.get("set_frames_startup")

    data = get_asset_data()

    if set_resolution_startup:
        set_resolution(data)
    if set_frames_startup:
        set_frame_range(data)

    unit_scale_settings = settings.get("unit_scale_settings")
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


def _discover_gui() -> Optional[Callable]:
    """Return the most desirable of the currently registered GUIs"""

    # Prefer last registered
    guis = reversed(pyblish.api.registered_guis())

    for gui in guis:
        try:
            gui = __import__(gui).show
        except (ImportError, AttributeError):
            continue
        else:
            return gui

    return None


def add_to_avalon_container(container: bpy.types.Collection):
    """Add the container to the Avalon container."""

    avalon_container = bpy.data.collections.get(AVALON_CONTAINERS)
    if not avalon_container:
        avalon_container = bpy.data.collections.new(name=AVALON_CONTAINERS)

        # Link the container to the scene so it's easily visible to the artist
        # and can be managed easily. Otherwise it's only found in "Blender
        # File" view and it will be removed by Blenders garbage collection,
        # unless you set a 'fake user'.
        bpy.context.scene.collection.children.link(avalon_container)

    avalon_container.children.link(container)

    # Disable Avalon containers for the view layers.
    for view_layer in bpy.context.scene.view_layers:
        for child in view_layer.layer_collection.children:
            if child.collection == avalon_container:
                child.exclude = True


def metadata_update(node: bpy.types.bpy_struct_meta_idprop, data: Dict):
    """Imprint the node with metadata.

    Existing metadata will be updated.
    """

    if not node.get(AVALON_PROPERTY):
        node[AVALON_PROPERTY] = dict()
    for key, value in data.items():
        if value is None:
            continue
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
    add_to_avalon_container(container)

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
    add_to_avalon_container(container)

    return container


def parse_container(container: bpy.types.Collection,
                    validate: bool = True) -> Dict:
    """Return the container node's full container data.

    Args:
        container: A container node name.
        validate: turn the validation for the container on or off

    Returns:
        The container schema data for this container node.

    """

    data = lib.read(container)

    # Append transient data
    data["objectName"] = container.name

    if validate:
        schema.validate(data)

    return data


def ls() -> Iterator:
    """List containers from active Blender scene.

    This is the host-equivalent of api.ls(), but instead of listing assets on
    disk, it lists assets already loaded in Blender; once loaded they are
    called containers.
    """

    for container in lib.lsattr("id", AVALON_CONTAINER_ID):
        yield parse_container(container)


def publish():
    """Shorthand to publish from within host."""

    return pyblish.util.publish()
