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
import bpy.utils.previews

from openpype import style
from openpype.pipeline import get_current_asset_name, get_current_task_name
from openpype.pipeline import legacy_io, Anatomy
from openpype.tools.utils import host_tools
from openpype.modules.base import ModulesManager
from .lib import download_last_workfile
from . import pipeline
from openpype.tools.utils.lib import qt_app_context
from .workio import (
    OpenFileCacher,
    check_workfile_up_to_date,
)

PREVIEW_COLLECTIONS: Dict = dict()

# This seems like a good value to keep the Qt app responsive and doesn't slow
# down Blender. At least on macOS I the interface of Blender gets very laggy if
# you make it smaller.
TIMER_INTERVAL: float = 0.01 if platform.system() == "Windows" else 0.1


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
            {"asset": get_current_asset_name()},
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


class LaunchWorkFiles(LaunchQtApp):
    """Launch Avalon Work Files."""

    bl_idname = "wm.avalon_workfiles"
    bl_label = "Work Files..."
    _tool_name = "workfiles"

    def execute(self, context):
        result = super().execute(context)
        self._window.set_context({
            "asset": get_current_asset_name(),
            "task": get_current_task_name()
        })
        return result

    def before_window_show(self):
        self._window.root = str(Path(
            os.environ.get("AVALON_WORKDIR", ""),
            os.environ.get("AVALON_SCENEDIR", ""),
        ))
        self._window.refresh()


class SetFrameRange(bpy.types.Operator):
    bl_idname = "wm.ayon_set_frame_range"
    bl_label = "Set Frame Range"

    def execute(self, context):
        data = pipeline.get_asset_data()
        pipeline.set_frame_range(data)
        return {"FINISHED"}


class SetResolution(bpy.types.Operator):
    bl_idname = "wm.ayon_set_resolution"
    bl_label = "Set Resolution"

    def execute(self, context):
        data = pipeline.get_asset_data()
        pipeline.set_resolution(data)
        return {"FINISHED"}

class WM_OT_CheckWorkfileUpToDate(bpy.types.Operator):
    """Check if the current workfile is up to date.

    If it's out of date, the workfile out of date dialog will open.
    Otherwise, a dialog notifying user that their workfile is up to date will
    appear.
    """

    bl_idname = "wm.check_workfile_up_to_date"
    bl_label = "Check Workfile Up To Date"

    action: bpy.props.EnumProperty(
        name="Action Enum",
        items=(
            ("DOWNLOAD", "Download last workfile", "Download last workfile"),
            ("QUIT", "Quit blender", "Quit blender"),
            ("PROCEED", "Proceed anyway", "Proceed anyway AT YOUR OWN RISK"),
        ),
    )

    def invoke(self, context, _event):
        """Invoke this operator."""
        context.scene.is_workfile_up_to_date = check_workfile_up_to_date()
        if context.scene.is_workfile_up_to_date:
            return context.window_manager.invoke_popup(self)
        else:
            return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        """Draw UI."""
        if context.scene.is_workfile_up_to_date:
            layout = self.layout
            layout.ui_units_x = 7.5
            layout.label(text="Your workfile is up to date!")
        else:
            col = self.layout.column()

            # Display alert
            row = col.row()
            row.alert = True
            row.label(text="Your workfile is out of date.")

            # Display enum
            col.prop(self, "action", expand=True)

    def execute(self, context):
        """Execute this operator."""
        # Check workfile is up to date
        if context.scene.is_workfile_up_to_date:
            return {"FINISHED"}

        if self.action == "DOWNLOAD":
            context.window.cursor_set("WAIT")

            # Get sync server module
            sync_server = ModulesManager().modules_by_name.get("sync_server")
            if not sync_server or not sync_server.enabled:
                self.report(
                    {"WARNING"},
                    "Sync server module is disabled or unavailable.",
                )
                return {"CANCELLED"}

            last_workfile_path, last_published_time = download_last_workfile()
            if last_workfile_path:
                bpy.ops.wm.open_mainfile(filepath=last_workfile_path)

                # Update variables
                context.scene["op_published_time"] = last_published_time
                context.scene.is_workfile_up_to_date = True

                bpy.ops.wm.save_mainfile()
                bpy.ops.wm.revert_mainfile()
                return {"FINISHED"}
            else:
                self.report({"ERROR"}, "Failed to download last workfile.")
                return {"CANCELLED"}
        elif self.action == "QUIT":
            bpy.ops.wm.quit_blender()
            return {"FINISHED"}
        elif self.action == "PROCEED":
            return {"FINISHED"}
        else:
            self.report({"ERROR"}, "Undefined enum value error")
            return {"CANCELLED"}

    def cancel(self, context):
        """Run when this operator is cancelled."""
        if not context.scene.is_workfile_up_to_date:
            bpy.ops.wm.check_workfile_up_to_date("INVOKE_DEFAULT")


class TOPBAR_MT_avalon(bpy.types.Menu):
    """Avalon menu."""

    bl_idname = "TOPBAR_MT_avalon"
    bl_label = os.environ.get("AVALON_LABEL")

    def draw(self, context):
        """Draw the menu in the UI."""

        layout = self.layout

        # Display workfile out of date warning
        if not context.scene.is_workfile_up_to_date:
            row = layout.row()
            row.operator(
                WM_OT_CheckWorkfileUpToDate.bl_idname,
                text="Your workfile is out of date!",
                icon="ERROR",
            )
            layout.separator()

        pcoll = PREVIEW_COLLECTIONS.get("avalon")
        if pcoll:
            pyblish_menu_icon = pcoll["pyblish_menu_icon"]
            pyblish_menu_icon_id = pyblish_menu_icon.icon_id
        else:
            pyblish_menu_icon_id = 0

        asset = get_current_asset_name()
        task = get_current_task_name()
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
        layout.operator(SetFrameRange.bl_idname, text="Set Frame Range")
        layout.operator(SetResolution.bl_idname, text="Set Resolution")
        layout.separator()
        layout.operator(LaunchWorkFiles.bl_idname, text="Work Files...")
        # TODO (jasper): maybe add 'Reload Pipeline', 'Reset Frame Range' and
        #                'Reset Resolution'?
        layout.separator()
        layout.operator(WM_OT_CheckWorkfileUpToDate.bl_idname)


def draw_avalon_menu(self, context):
    """Draw the Avalon menu in the top bar."""

    self.layout.menu(
        TOPBAR_MT_avalon.bl_idname,
        icon="ERROR"
        if not context.scene.is_workfile_up_to_date
        else "NONE",
    )



classes = [
    LaunchCreator,
    LaunchLoader,
    LaunchPublisher,
    LaunchManager,
    LaunchLibrary,
    LaunchWorkFiles,
    SetFrameRange,
    SetResolution,
    WM_OT_CheckWorkfileUpToDate,
    TOPBAR_MT_avalon,
]


def update_workfile_up_to_date():
    """Check regularily the current workfile is up-to-date."""
    bpy.context.scene.is_workfile_up_to_date = check_workfile_up_to_date()
    return 60 * 10


def register():
    "Register the operators and menu."

    pcoll = bpy.utils.previews.new()
    pyblish_icon_file = Path(__file__).parent / "icons" / "pyblish-32x32.png"
    pcoll.load("pyblish_menu_icon", str(pyblish_icon_file.absolute()), 'IMAGE')
    PREVIEW_COLLECTIONS["avalon"] = pcoll

    BlenderApplication.get_app()
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_editor_menus.append(draw_avalon_menu)

    # Regularily check the workfile is up-to-date
    bpy.app.timers.register(
        update_workfile_up_to_date, first_interval=0, persistent=True
    )

    # Use a timer to delay execution of check_workfile_up_to_date
    def delayed_check_workfile_up_to_date():
        if hasattr(
            bpy.types, bpy.ops.wm.check_workfile_up_to_date.idname()
        ):
            bpy.ops.wm.check_workfile_up_to_date("INVOKE_DEFAULT")
    bpy.app.timers.register(delayed_check_workfile_up_to_date, persistent=True)

def unregister():
    """Unregister the operators and menu."""

    pcoll = PREVIEW_COLLECTIONS.pop("avalon")
    bpy.utils.previews.remove(pcoll)
    bpy.types.TOPBAR_MT_editor_menus.remove(draw_avalon_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    bpy.app.timers.unregister(check_workfile_up_to_date)
