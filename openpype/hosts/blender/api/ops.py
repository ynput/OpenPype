"""Blender operators and menus for use with Avalon."""

import os
import sys
import platform
import time
import traceback
import collections
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Optional, Union

from qtpy import QtWidgets, QtCore

import bpy
from bpy.props import EnumProperty
import bpy.utils.previews

from openpype import style
from openpype.client.entities import get_assets, get_asset_by_name, get_subset_by_id, get_version_by_id
from openpype.hosts.blender.api.lib import ls
from openpype.pipeline import legacy_io
from openpype.pipeline.constants import AVALON_INSTANCE_ID
from openpype.pipeline.create.creator_plugins import discover_legacy_creator_plugins, get_legacy_creator_by_name
from openpype.pipeline.create.subset_name import get_subset_name
from openpype.tools.utils import host_tools

from .workio import OpenFileCacher

PREVIEW_COLLECTIONS: Dict = dict()

# This seems like a good value to keep the Qt app responsive and doesn't slow
# down Blender. At least on macOS I the interface of Blender gets very laggy if
# you make it smaller.
TIMER_INTERVAL: float = 0.01 if platform.system() == "Windows" else 0.1

# Match Blender type to a datapath to look into. Needed for native UI creator.
BL_TYPE_DATAPATH = {
    bpy.types.Collection: "bpy.context.scene.collection.children",
    bpy.types.Object: "bpy.context.scene.collection.all_objects",
    bpy.types.Camera: "bpy.data.cameras",
    bpy.types.Action: "bpy.data.actions",
    bpy.types.Armature: "bpy.data.armatures",
}


class BlenderApplication(QtWidgets.QApplication):
    _instance = None
    blender_windows = {}

    def __init__(self, *args, **kwargs):
        super(BlenderApplication, self).__init__(*args, **kwargs)
        self.setQuitOnLastWindowClosed(False)

        self.setStyleSheet(style.load_stylesheet())
        self.lastWindowClosed.connect(self.__class__.reset)

    @classmethod
    def get_app(cls):
        if cls._instance is None:
            cls._instance = cls(sys.argv)
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    @classmethod
    def store_window(cls, identifier, window):
        current_window = cls.get_window(identifier)
        cls.blender_windows[identifier] = window
        if current_window:
            current_window.close()
            # current_window.deleteLater()

    @classmethod
    def get_window(cls, identifier):
        return cls.blender_windows.get(identifier)


class MainThreadItem:
    """Structure to store information about callback in main thread.

    Item should be used to execute callback in main thread which may be needed
    for execution of Qt objects.

    Item store callback (callable variable), arguments and keyword arguments
    for the callback. Item hold information about it's process.
    """
    not_set = object()
    sleep_time = 0.1

    def __init__(self, callback, *args, **kwargs):
        self.done = False
        self.exception = self.not_set
        self.result = self.not_set
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def execute(self):
        """Execute callback and store its result.

        Method must be called from main thread. Item is marked as `done`
        when callback execution finished. Store output of callback of exception
        information when callback raises one.
        """
        print("Executing process in main thread")
        if self.done:
            print("- item is already processed")
            return

        callback = self.callback
        args = self.args
        kwargs = self.kwargs
        print("Running callback: {}".format(str(callback)))
        try:
            result = callback(*args, **kwargs)
            self.result = result

        except Exception:
            self.exception = sys.exc_info()

        finally:
            print("Done")
            self.done = True

    def wait(self):
        """Wait for result from main thread.

        This method stops current thread until callback is executed.

        Returns:
            object: Output of callback. May be any type or object.

        Raises:
            Exception: Reraise any exception that happened during callback
                execution.
        """
        while not self.done:
            print(self.done)
            time.sleep(self.sleep_time)

        if self.exception is self.not_set:
            return self.result
        raise self.exception


class GlobalClass:
    app = None
    main_thread_callbacks = collections.deque()
    is_windows = platform.system().lower() == "windows"


def execute_in_main_thread(main_thead_item):
    print("execute_in_main_thread")
    GlobalClass.main_thread_callbacks.append(main_thead_item)


def _process_app_events() -> Optional[float]:
    """Process the events of the Qt app if the window is still visible.

    If the app has any top level windows and at least one of them is visible
    return the time after which this function should be run again. Else return
    None, so the function is not run again and will be unregistered.
    """
    while GlobalClass.main_thread_callbacks:
        main_thread_item = GlobalClass.main_thread_callbacks.popleft()
        main_thread_item.execute()
        if main_thread_item.exception is not MainThreadItem.not_set:
            _clc, val, tb = main_thread_item.exception
            msg = str(val)
            detail = "\n".join(traceback.format_exception(_clc, val, tb))
            dialog = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning,
                "Error",
                msg)
            dialog.setMinimumWidth(500)
            dialog.setDetailedText(detail)
            dialog.setWindowFlags(
                dialog.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
            )

            dialog.exec_()

        # Refresh Manager
        if GlobalClass.app:
            manager = GlobalClass.app.get_window("WM_OT_avalon_manager")
            if manager:
                manager.refresh()

    if not GlobalClass.is_windows:
        if OpenFileCacher.opening_file:
            return TIMER_INTERVAL

        app = GlobalClass.app
        if app._instance:
            app.processEvents()
            return TIMER_INTERVAL
    return TIMER_INTERVAL


class LaunchQtApp(bpy.types.Operator):
    """A Base class for opertors to launch a Qt app."""

    _app: QtWidgets.QApplication
    _window = Union[QtWidgets.QDialog, ModuleType]
    _tool_name: str = None
    _init_args: Optional[List] = list()
    _init_kwargs: Optional[Dict] = dict()
    bl_idname: str = None

    def __init__(self):
        if self.bl_idname is None:
            raise NotImplementedError("Attribute `bl_idname` must be set!")
        print(f"Initialising {self.bl_idname}...")
        self._app = BlenderApplication.get_app()
        GlobalClass.app = self._app

        if not bpy.app.timers.is_registered(_process_app_events):
            bpy.app.timers.register(
                _process_app_events,
                persistent=True
            )

    def execute(self, context):
        """Execute the operator.

        The child class must implement `execute()` where it only has to set
        `self._window` to the desired Qt window and then simply run
        `return super().execute(context)`.
        `self._window` is expected to have a `show` method.
        If the `show` method requires arguments, you can set `self._show_args`
        and `self._show_kwargs`. `args` should be a list, `kwargs` a
        dictionary.
        """

        if self._tool_name is None:
            if self._window is None:
                raise AttributeError("`self._window` is not set.")

        else:
            window = self._app.get_window(self.bl_idname)
            if window is None:
                window = host_tools.get_tool_by_name(self._tool_name)
                self._app.store_window(self.bl_idname, window)
            self._window = window

        if not isinstance(self._window, (QtWidgets.QWidget, ModuleType)):
            raise AttributeError(
                "`window` should be a `QWidget or module`. Got: {}".format(
                    str(type(window))
                )
            )

        self.before_window_show()

        if isinstance(self._window, ModuleType):
            self._window.show()
            window = None
            if hasattr(self._window, "window"):
                window = self._window.window
            elif hasattr(self._window, "_window"):
                window = self._window.window

            if window:
                self._app.store_window(self.bl_idname, window)

        else:
            origin_flags = self._window.windowFlags()
            on_top_flags = origin_flags | QtCore.Qt.WindowStaysOnTopHint
            self._window.setWindowFlags(on_top_flags)
            self._window.show()

            # if on_top_flags != origin_flags:
            #     self._window.setWindowFlags(origin_flags)
            #     self._window.show()

        return {'FINISHED'}

    def before_window_show(self):
        return


class LaunchCreator(LaunchQtApp):
    """Launch Avalon Creator."""

    bl_idname = "wm.avalon_creator"
    bl_label = "Create..."
    _tool_name = "creator"

    def before_window_show(self):
        self._window.refresh()


class LaunchLoader(LaunchQtApp):
    """Launch Avalon Loader."""

    bl_idname = "wm.avalon_loader"
    bl_label = "Load..."
    _tool_name = "loader"

    def before_window_show(self):
        self._window.set_context(
            {"asset": legacy_io.Session["AVALON_ASSET"]},
            refresh=True
        )


class LaunchPublisher(LaunchQtApp):
    """Launch Avalon Publisher."""

    bl_idname = "wm.avalon_publisher"
    bl_label = "Publish..."

    def execute(self, context):
        host_tools.show_publish()
        return {"FINISHED"}


class LaunchManager(LaunchQtApp):
    """Launch Avalon Manager."""

    bl_idname = "wm.avalon_manager"
    bl_label = "Manage..."
    _tool_name = "sceneinventory"

    def before_window_show(self):
        self._window.refresh()


class LaunchLibrary(LaunchQtApp):
    """Launch Library Loader."""

    bl_idname = "wm.library_loader"
    bl_label = "Library..."
    _tool_name = "libraryloader"

    def before_window_show(self):
        self._window.refresh()


def _update_entries_preset(self, _context):
    """Update some entries with a preset.

    - Set `datapath`'s value to the first item of the list to avoid `None` values when
    the length of the items list reduces.
    - Update variant name to the first item. TODO available variant names
    """
    creator_plugin = get_legacy_creator_by_name(self.creator)

    # Set default datapath
    self.datapath = BL_TYPE_DATAPATH.get(creator_plugin.bl_types[0])

    # Change names
    # Check if Creator plugin has set defaults
    if creator_plugin.defaults and isinstance(
        creator_plugin.defaults, (list, tuple, set)
    ):
        self.variant_default = creator_plugin.defaults[0]


def _update_subset_name(self: bpy.types.Operator, _context: bpy.types.Context):
    """Update subset name by getting the family name from the creator plugin.

    Args:
        self (bpy.types.Operator): Current running operator
        _context (bpy.types.Context): Current context
    """
    project_name = legacy_io.active_project()
    asset_doc = get_asset_by_name(
        project_name, self.asset_name, fields=["_id"]
    )
    task_name = legacy_io.Session["AVALON_TASK"]

    # Get creator plugin
    creator_plugin = get_legacy_creator_by_name(self.creator)

    # Build subset name and set it
    self.subset_name = get_subset_name(
        creator_plugin.family,
        self.variant_name,
        task_name,
        asset_doc,
        project_name,
    )


def _update_variant_name(
    self: bpy.types.Operator, _context: bpy.types.Context
):
    """Update subset name by getting the family name from the creator plugin.

    Args:
        self (bpy.types.Operator): Current running operator
        _context (bpy.types.Context): Current context
    """
    self.variant_name = self.variant_default


class SimpleOperator(bpy.types.Operator):
    """Create OpenPype instance"""

    bl_idname = "scene.simple_operator"
    bl_label = "Simple Object Operator"
    bl_options = {"REGISTER", "UNDO"}

    creator: EnumProperty(
        name="Creator",
        # Items from all creator plugins, referenced by their class name, label is displayed in UI
        # creator class name is used later to get the creator plugin
        items=lambda _, __: (
            (p.__name__, p.label, "")
            for p in discover_legacy_creator_plugins()
        ),
        update=_update_entries_preset,
    )

    all_assets: bpy.props.CollectionProperty(
        name="Asset Name",
        type=bpy.types.PropertyGroup,
    )
    asset_name: bpy.props.StringProperty(name="Asset Name")

    # Variant
    variant_name: bpy.props.StringProperty(
        name="Variant Name", update=_update_subset_name
    )
    variant_default: EnumProperty(
        name="Variant Defaults",
        # Items are defaults from current creator plugin
        items=lambda self, _: [
            (default, default, "")
            for default in get_legacy_creator_by_name(self.creator).defaults
        ],
        update=_update_variant_name,
    )

    subset_name: bpy.props.StringProperty(name="Subset Name")
    use_selection: bpy.props.BoolProperty(name="Use selection")
    datapath: EnumProperty(
        name="Data type",
        # Build datapath items by getting the creator by its name
        # Matching the appropriate datapath using the bl_types field which lists all relevant data types
        items=lambda self, _: [
            (BL_TYPE_DATAPATH.get(bl_type), bl_type.__name__, "")
            for bl_type in get_legacy_creator_by_name(self.creator).bl_types
        ],
    )
    datablock: bpy.props.StringProperty(name="Datablock")

    def __init__(self) -> None:
        # Set assets list
        self.all_assets.clear()
        for asset_doc in get_assets(legacy_io.active_project()):
            self.all_assets.add().name = asset_doc["name"]
            
        self.asset_name = legacy_io.Session["AVALON_ASSET"]

        # Setup all data
        _update_entries_preset(self, None)

        # Determine use_selection
        self.use_selection = bool(bpy.context.selected_objects)

    def invoke(self, context, _event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, _context):
        layout = self.layout

        layout.prop(self, "creator")
        layout.prop_search(self, "asset_name", self, "all_assets")

        # Variant with defaults list
        sublayout = layout.row(align=True)
        sublayout.prop(self, "variant_name")
        sublayout.prop(self, "variant_default", icon_only=True)

        # Subset name preview
        sublayout = layout.row()
        sublayout.enabled = False
        sublayout.prop(self, "subset_name")

        # Use selection only if relevant to outliner data
        if self.datapath.startswith("bpy.context.scene"):
            sublayout = layout.row()
            # Enabled only if objects selected
            sublayout.enabled = bool(bpy.context.selected_objects)
            sublayout.prop(self, "use_selection")

        # If not use selection, pick the datablock in a field
        if not self.use_selection:
            row = layout.row(align=True)

            creator_plugin = get_legacy_creator_by_name(self.creator)

            # Search data into list
            data_path, search_field = self.datapath.rsplit(
                ".", 1
            )  # Split data path from search field
            row.prop_search(
                self, "datablock", eval(data_path), search_field, text=""
            ) if self.datapath else layout.label(
                text=f"Not supported family: {self.creator}"
            )

            # Pick list if several possibilities match
            if len(creator_plugin.bl_types) > 1:
                row.prop(self, "datapath", text="", icon_only=True)

    def execute(self, _context):
        if not self.asset_name:
            self.report({"ERROR"}, f"Asset name must be filled!")
            return {"CANCELLED"}

        # Get creator class
        Creator = get_legacy_creator_by_name(self.creator)

        # NOTE Shunting legacy_create because of useless overhead and deprecated design. 
        # Will see if compatible with new creator when implemented for Blender
        plugin = Creator(self.subset_name, self.asset_name, {"variant": self.variant_name})
        datapath = eval(self.datapath)
        plugin._process(bpy.context.selected_objects if self.use_selection else [datapath.get(self.datablock)])
        
        if not self.datablock and not self.use_selection:
            self.report({'WARNING'}, f"No any datablock to process...")

        return {"FINISHED"}


class LaunchWorkFiles(LaunchQtApp):
    """Launch Avalon Work Files."""

    bl_idname = "wm.avalon_workfiles"
    bl_label = "Work Files..."
    _tool_name = "workfiles"

    def execute(self, context):
        result = super().execute(context)
        self._window.set_context({
            "asset": legacy_io.Session["AVALON_ASSET"],
            "task": legacy_io.Session["AVALON_TASK"]
        })
        return result

    def before_window_show(self):
        self._window.root = str(Path(
            os.environ.get("AVALON_WORKDIR", ""),
            os.environ.get("AVALON_SCENEDIR", ""),
        ))
        self._window.refresh()


class TOPBAR_MT_avalon(bpy.types.Menu):
    """Avalon menu."""

    bl_idname = "TOPBAR_MT_avalon"
    bl_label = os.environ.get("AVALON_LABEL")

    def draw(self, context):
        """Draw the menu in the UI."""

        layout = self.layout

        pcoll = PREVIEW_COLLECTIONS.get("avalon")
        if pcoll:
            pyblish_menu_icon = pcoll["pyblish_menu_icon"]
            pyblish_menu_icon_id = pyblish_menu_icon.icon_id
        else:
            pyblish_menu_icon_id = 0

        asset = legacy_io.Session['AVALON_ASSET']
        task = legacy_io.Session['AVALON_TASK']
        context_label = f"{asset}, {task}"
        context_label_item = layout.row()
        context_label_item.operator(
            LaunchWorkFiles.bl_idname, text=context_label
        )
        context_label_item.enabled = False
        layout.separator()
        layout.operator(LaunchCreator.bl_idname, text="Create...")
        layout.operator(LaunchLoader.bl_idname, text="Load...")
        layout.operator(
            LaunchPublisher.bl_idname,
            text="Publish...",
            icon_value=pyblish_menu_icon_id,
        )
        layout.operator(LaunchManager.bl_idname, text="Manage...")
        layout.operator(LaunchLibrary.bl_idname, text="Library...")
        layout.separator()
        layout.operator(LaunchWorkFiles.bl_idname, text="Work Files...")
        # TODO (jasper): maybe add 'Reload Pipeline', 'Set Frame Range' and
        #                'Set Resolution'?


def draw_avalon_menu(self, context):
    """Draw the Avalon menu in the top bar."""

    self.layout.menu(TOPBAR_MT_avalon.bl_idname)


class SCENE_OT_MakeContainerPublishable(bpy.types.Operator):
    """Convert loaded container to a publishable one"""

    bl_idname = "scene.make_container_publishable"
    bl_label = "Make Container Publishable"

    container_name: bpy.props.StringProperty(
        name="Container to make publishable"
    )

    # NOTE cannot use AVALON_PROPERTY because of circular dependency
    # and the refactor is very big, but must be done soon

    @classmethod
    def poll(cls, context):
        # Check selected collection is in loaded containers
        if context.collection is not context.scene.collection:
            return context.collection.name in {
                container["objectName"] for container in ls()
            }

    def execute(self, context):
        if not self.container_name:
            self.report({"WARNING"}, "No container to make publishable...")
            return {"CANCELLED"}

        # Recover required data
        container_collection = bpy.data.collections.get(self.container_name)
        avalon_data = container_collection["avalon"]
        project_name = legacy_io.current_project()
        version_doc = get_version_by_id(project_name, avalon_data["parent"])
        subset_doc = get_subset_by_id(project_name, version_doc["parent"])

        # Build and update metadata
        metadata = {
            "id": AVALON_INSTANCE_ID,
            "family": avalon_data["family"],
            "asset": avalon_data["asset_name"],
            "subset": subset_doc["name"],
            "task": legacy_io.Session.get("AVALON_TASK"),
            "active": True,
        }
        container_collection["avalon"] = metadata
        return {"FINISHED"}


def draw_op_collection_menu(self, context):
    """Draw OpenPype collection context menu.

    Args:
        context (bpy.types.Context): Current Blender Context
    """
    layout = self.layout
    layout.separator()
    op = layout.operator(
        SCENE_OT_MakeContainerPublishable.bl_idname,
        text=SCENE_OT_MakeContainerPublishable.bl_label,
    )
    op.container_name = context.collection.name


classes = [
    LaunchCreator,
    LaunchLoader,
    LaunchPublisher,
    LaunchManager,
    LaunchLibrary,
    LaunchWorkFiles,
    TOPBAR_MT_avalon,
    SCENE_OT_MakeContainerPublishable,
    SimpleOperator,
]


def register():
    "Register the operators and menu."

    pcoll = bpy.utils.previews.new()
    pyblish_icon_file = Path(__file__).parent / "icons" / "pyblish-32x32.png"
    pcoll.load("pyblish_menu_icon", str(pyblish_icon_file.absolute()), 'IMAGE')
    PREVIEW_COLLECTIONS["avalon"] = pcoll

    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_editor_menus.append(draw_avalon_menu)

    # Add make_container_publishable to collection and outliner menus
    bpy.types.OUTLINER_MT_collection.append(draw_op_collection_menu)
    bpy.types.OUTLINER_MT_context_menu.append(draw_op_collection_menu)


def unregister():
    """Unregister the operators and menu."""

    pcoll = PREVIEW_COLLECTIONS.pop("avalon")
    bpy.utils.previews.remove(pcoll)
    bpy.types.TOPBAR_MT_editor_menus.remove(draw_avalon_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
