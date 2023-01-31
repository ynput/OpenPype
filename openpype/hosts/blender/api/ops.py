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
from bpy.app.handlers import persistent
from bpy.props import EnumProperty
import bpy.utils.previews

from openpype import style
from openpype.client.entities import (
    get_asset_by_name,
    get_assets,
    get_subset_by_id,
    get_version_by_id,
)
from openpype.hosts.blender.api.lib import ls
from openpype.hosts.blender.api.utils import (
    BL_OUTLINER_TYPES,
    BL_TYPE_DATAPATH,
)
from openpype.pipeline import legacy_io
from openpype.pipeline.constants import AVALON_INSTANCE_ID
from openpype.pipeline.create.creator_plugins import (
    discover_legacy_creator_plugins,
    get_legacy_creator_by_name,
)
from openpype.pipeline.create.subset_name import get_subset_name
from openpype.tools.utils import host_tools

from .workio import OpenFileCacher

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


def _update_entries_preset(self, context):
    """Update some entries with a preset.

    - Set `datapath`'s value to the first item of the list to avoid `None`
    values when the length of the items list reduces.
    - Update variant name to the first item.
    """
    creator_params = context.scene["openpype_creators"][self.creator_name]

    # Set default datapath and datablock
    self.datapath = creator_params["bl_types"][0][0]
    self.datablock_name = ""

    # Change names
    # Check if Creator plugin has set defaults
    if creator_params["defaults"] and isinstance(
        creator_params["defaults"], (list, tuple, set)
    ):
        self.variant_default = creator_params["defaults"][0]

    # Check if compatible with the outliner
    self.compatible_with_outliner = bool(
        {
            getattr(bpy.types, type_name)
            for _, type_name in creator_params["bl_types"]
        }
        & BL_OUTLINER_TYPES
    )
    if self.compatible_with_outliner:
        self.use_selection = bool(context.selected_objects)
    else:
        self.use_selection = False

    # Prefill data collection
    _update_datacol(self, context)


def _update_subset_name(self: bpy.types.Operator, context: bpy.types.Context):
    """Update subset name by getting the family name from the creator plugin.

    Args:
        self (bpy.types.Operator): Current running operator
        context (bpy.types.Context): Current context
    """
    if not self.asset_name:
        return

    project_name = legacy_io.active_project()
    asset_doc = get_asset_by_name(
        project_name, self.asset_name, fields=["_id"]
    )
    task_name = legacy_io.Session["AVALON_TASK"]

    # Get creator plugin
    creator_plugin = context.scene["openpype_creators"][self.creator_name]

    # Build subset name and set it
    self.subset_name = get_subset_name(
        creator_plugin["family"],
        self.variant_name,
        task_name,
        asset_doc,
        project_name,
    )


def _update_variant_name(
    self: bpy.types.Operator, _context: bpy.types.Context
):
    """Update variant name by setting the variant default

    Args:
        self (bpy.types.Operator): Current running operator
        _context (bpy.types.Context): Current context
    """
    self.variant_name = self.variant_default


def _update_datacol(self: bpy.types.Operator, context: bpy.types.Context):
    """At data collection update, automatically set the datablock name.

    Args:
        self (bpy.types.Operator): Current running operator
        context (bpy.types.Context): Current context
    """
    # Prefill with selected entity
    if (
        self.datapath == "collections"
        and context.collection != context.scene.collection
    ):
        active_entity = context.collection
    elif self.datapath == "objects":
        active_entity = context.active_object
    else:
        active_entity = None

    if active_entity:
        self.datablock_name = active_entity.name


class ManageOpenpypeInstance:
    """Properties to manage an OpenPype instance."""

    creator_name: EnumProperty(
        name="Creator",
        # Items from all creator plugins, referenced by their class name,
        # label is displayed in UI creator class name is used later to get
        # the creator plugin
        items=lambda _, context: (
            (name, params.get("label"), "")
            for name, params in context.scene["openpype_creators"].items()
        ),
        update=_update_entries_preset,
    )
    instance_name: bpy.props.StringProperty(name="Instance Name")

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
        items=lambda self, context: [
            (default, default, "")
            for default in context.scene["openpype_creators"][self.creator_name][
                "defaults"
            ]
        ],
        update=_update_variant_name,
    )

    subset_name: bpy.props.StringProperty(name="Subset Name")
    compatible_with_outliner: bpy.props.BoolProperty(
        name="Compatible with outliner"
    )
    use_selection: bpy.props.BoolProperty(name="Use selection")
    datapath: EnumProperty(
        name="Data type",
        # Build datapath items by getting the creator by its name
        # Matching the appropriate datapath using the bl_types field
        # which lists all relevant data types
        items=lambda self, context: [
            (datapath, name, "")
            for datapath, name in context.scene["openpype_creators"][
                self.creator_name
            ]["bl_types"]
        ],
        update=_update_datacol,
    )
    datablock_name: bpy.props.StringProperty(name="Datablock Name")

    gather_into_collection: bpy.props.BoolProperty(
        name="Gather into collection",
        description="Gather outliner entities when added to instance under single collection",
    )


class SCENE_OT_CreateOpenpypeInstance(
    ManageOpenpypeInstance, bpy.types.Operator
):
    """Create OpenPype instance"""

    bl_idname = "scene.create_openpype_instance"
    bl_label = "Create OpenPype Instance"
    bl_options = {"REGISTER", "UNDO"}

    def __init__(self):
        super().__init__()

        # Set assets list
        self.all_assets.clear()
        for asset_doc in get_assets(legacy_io.active_project()):
            self.all_assets.add().name = asset_doc["name"]

        self.asset_name = legacy_io.Session["AVALON_ASSET"]
        
        # Setup all data
        _update_entries_preset(self, bpy.context)

    def invoke(self, context, _event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "creator_name")
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
        if self.compatible_with_outliner:
            sublayout = layout.row()
            # Enabled only if objects selected
            sublayout.enabled = bool(bpy.context.selected_objects)
            sublayout.prop(self, "use_selection")

        # If not use selection, pick the datablock in a field
        if not self.use_selection:
            row = layout.row(align=True)

            creator_plugin = context.scene["openpype_creators"][self.creator_name]

            # Search data into list
            row.prop_search(
                self, "datablock_name", bpy.data, self.datapath, text=""
            ) if self.datapath else layout.label(
                text=f"Not supported family: {self.creator_name}"
            )

            # Pick list if several possibilities match
            if len(creator_plugin["bl_types"]) > 1:
                row.prop(self, "datapath", text="", icon_only=True)

        # Checkbox to gather selected element in outliner
        draw_gather_into_collection(self, context)


    def execute(self, _context):
        if not self.asset_name:
            self.report({"ERROR"}, f"Asset name must be filled!")
            return {"CANCELLED"}

        if not self.datablock_name and not self.use_selection:
            self.report({"WARNING"}, f"No any datablock to process...")

        # Get creator class
        Creator = get_legacy_creator_by_name(self.creator_name)

        # NOTE Shunting legacy_create because of useless overhead
        # and deprecated design.
        # Will see if compatible with new creator when implemented for Blender
        plugin = Creator(
            self.subset_name, self.asset_name, {"variant": self.variant_name}
        )
        datapath = getattr(bpy.data, self.datapath)
        plugin.process(
            bpy.context.selected_objects
            if self.use_selection
            else [datapath.get(self.datablock_name)],
            gather_into_collection=self.gather_into_collection
        )

        return {"FINISHED"}


class SCENE_OT_RemoveOpenpypeInstance(
    ManageOpenpypeInstance, bpy.types.Operator
):
    """Remove OpenPype instance"""

    bl_idname = "scene.remove_openpype_instance"
    bl_label = "Remove OpenPype Instance"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # Get openpype instance
        openpype_instances = context.scene.openpype_instances
        op_instance = openpype_instances.get(self.instance_name)

        # Get creator class
        Creator = get_legacy_creator_by_name(self.creator_name)

        # NOTE Shunting legacy_create because of useless overhead 
        # and deprecated design.
        # Will see if compatible with new creator when implemented for Blender
        avalon_prop = op_instance["avalon"]
        plugin = Creator(
            avalon_prop["subset"],
            avalon_prop["asset"],
            {"variant": op_instance.name},
        )
        plugin._remove_instance(self.instance_name)

        # Ensure active index is not out of range after deletion
        if context.scene.openpype_instance_active_index >= len(
            context.scene.openpype_instances
        ):
            context.scene.openpype_instance_active_index = (
                len(context.scene.openpype_instances) - 1
            )

        return {"FINISHED"}


class SCENE_OT_AddToOpenpypeInstance(
    ManageOpenpypeInstance, bpy.types.Operator
):
    """Add to OpenPype instance"""

    bl_idname = "scene.add_to_openpype_instance"
    bl_label = "Add to OpenPype Instance"
    bl_options = {"REGISTER", "UNDO"}

    # Used to determine either the datatype enum must be displayed or not
    bl_types_count = bpy.props.IntProperty()

    def __init__(self):
        super().__init__()

        self.bl_types_count = len(
            bpy.context.scene["openpype_creators"][self.creator_name]["bl_types"]
        )

    def invoke(self, context, _event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout

        # Pick the datablock in a field
        row = layout.row(align=True)

        # Search data into list
        row.prop_search(
            self, "datablock_name", bpy.data, self.datapath, text=""
        )

        # Pick list if several possibilities match
        if self.bl_types_count > 1:
            row.prop(self, "datapath", text="", icon_only=True)

        # Checkbox to gather selected element in outliner
        draw_gather_into_collection(self, context)

    def execute(self, context):
        # Get datablock
        datapath = getattr(bpy.data, self.datapath)
        datablock = datapath.get(self.datablock_name)

        # Get openpype instance
        openpype_instances = context.scene.openpype_instances
        op_instance = openpype_instances.get(self.instance_name)

        # Check datablock is not already in instance
        if datablock in {
            d_ref.datablock for d_ref in op_instance.datablock_refs
        }:
            self.report(
                {"INFO"}, f"{datablock.name} already in {op_instance.name}."
            )
            return {"CANCELLED"}

        # Get creator class
        Creator = get_legacy_creator_by_name(self.creator_name)

        # NOTE Shunting legacy_create because of useless overhead and
        # deprecated design.
        # Will see if compatible with new creator when implemented for Blender
        avalon_prop = op_instance["avalon"]
        plugin = Creator(
            avalon_prop["subset"],
            avalon_prop["asset"],
            {"variant": op_instance.name},
        )
        datapath = getattr(bpy.data, self.datapath)
        plugin.process(
            [datablock], gather_into_collection=self.gather_into_collection
        )

        # Set active index to newly created
        op_instance.datablock_active_index = (
            len(op_instance.datablock_refs) - 1
        )

        return {"FINISHED"}



def draw_gather_into_collection(self, context):
    """Draw checkbox to gather selected element in outliner.
    
    Only if collections are handled by creator family.
    """
    if self.datapath in {BL_TYPE_DATAPATH.get(t) for t in BL_OUTLINER_TYPES} and bpy.types.Collection.__name__ in {
        t[1]
        for t in context.scene["openpype_creators"][self.creator_name][
            "bl_types"
        ]
    }:
        self.layout.prop(self, "gather_into_collection")


class SCENE_OT_RemoveFromOpenpypeInstance(
    ManageOpenpypeInstance, bpy.types.Operator
):
    """Remove from OpenPype instance"""

    bl_idname = "scene.remove_from_openpype_instance"
    bl_label = "Remove from OpenPype Instance"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        openpype_instances = context.scene.openpype_instances
        op_instance = openpype_instances.get(self.instance_name)

        # Remove from datablocks and restore original fake user state
        d_ref_index = op_instance.datablock_refs.find(self.datablock_name)
        d_ref = op_instance.datablock_refs[d_ref_index]
        d_ref.datablock.use_fake_user = d_ref.keep_fake_user
        op_instance.datablock_refs.remove(d_ref_index)

        # Ensure active index is not out of range after deletion
        if op_instance.datablock_active_index >= len(
            op_instance.datablock_refs
        ):
            op_instance.datablock_active_index = (
                len(op_instance.datablock_refs) - 1
            )

        return {"FINISHED"}

class SCENE_OT_MoveOpenpypeInstance(bpy.types.Operator):
    bl_idname = "scene.move_openpype_instance"
    bl_label = "Move Openpype Instance"
    bl_options = {"UNDO", "INTERNAL"}
    bl_description = "Change index of active openpype instance"

    direction: bpy.props.EnumProperty(
        items=(
            ("UP", "Up", ""),
            ("DOWN", "Down", ""),
        )
    )

    @classmethod
    def poll(cls, context):
        return len(context.scene.openpype_instances) > 0

    def execute(self, context):
        op_instances = context.scene.openpype_instances
        idx = context.scene.openpype_instance_active_index

        # down
        if self.direction == "DOWN":
            if idx < len(op_instances) - 1:
                op_instances.move(idx, idx + 1)
                context.scene.openpype_instance_active_index += 1

                self.report({"INFO"}, "Instance moved down")
            else:
                self.report({"INFO"}, "Unable to move in this direction")

        # up
        elif self.direction == "UP":
            if idx >= 1:
                op_instances.move(idx, idx - 1)
                context.scene.openpype_instance_active_index -= 1

                self.report({"INFO"}, "Instance moved up")
            else:
                self.report({"INFO"}, "Unable to move in this direction")

        return {"FINISHED"}


class SCENE_OT_MoveOpenpypeInstanceDatablock(bpy.types.Operator):
    bl_idname = "scene.move_openpype_instance_datablock"
    bl_label = "Move Openpype Instance Datablock"
    bl_description = "Change index of active openpype instance datablock"

    direction: bpy.props.EnumProperty(
        items=(
            ("UP", "Up", ""),
            ("DOWN", "Down", ""),
        )
    )

    @classmethod
    def poll(cls, context):
        active_instance = context.scene.openpype_instances[
            context.scene.openpype_instance_active_index
        ]
        return len(active_instance.datablock_refs) > 0

    def execute(self, context):
        active_instance = context.scene.openpype_instances[
            context.scene.openpype_instance_active_index
        ]
        idx = context.scene.openpype_instance_active_index

        # down
        if self.direction == "DOWN":
            if idx < len(active_instance.datablock_refs) - 1:
                active_instance.datablock_refs.move(idx, idx + 1)
                active_instance.datablock_active_index -= 1

                self.report({"INFO"}, "Instance Datablock moved down")
            else:
                self.report({"INFO"}, "Unable to move in this direction")

        # up
        elif self.direction == "UP":
            if idx >= 1:
                active_instance.datablock_refs.move(idx, idx - 1)
                active_instance.datablock_active_index -= 1

                self.report({"INFO"}, "Instance Datablock moved up")
            else:
                self.report({"INFO"}, "Unable to move in this direction")

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


@persistent
def discover_creators_handler(_):
    """Store creators parameters in scene for optimization."""
    plugins = discover_legacy_creator_plugins()
    bpy.context.scene["openpype_creators"] = {}
    for creator in plugins:
        bpy.context.scene["openpype_creators"][creator.__name__] = {
            "label": creator.label,
            "defaults": creator.defaults,
            "family": creator.family,
            "bl_types": [
                (BL_TYPE_DATAPATH.get(t), t.__name__) for t in creator.bl_types
            ],
        }


classes = [
    LaunchCreator,
    LaunchLoader,
    LaunchPublisher,
    LaunchManager,
    LaunchLibrary,
    LaunchWorkFiles,
    TOPBAR_MT_avalon,
    SCENE_OT_MakeContainerPublishable,
    SCENE_OT_CreateOpenpypeInstance,
    SCENE_OT_RemoveOpenpypeInstance,
    SCENE_OT_AddToOpenpypeInstance,
    SCENE_OT_RemoveFromOpenpypeInstance,
    SCENE_OT_MoveOpenpypeInstance,
    SCENE_OT_MoveOpenpypeInstanceDatablock,
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

    # Hack to store creators with parameters for optimization purpose
    bpy.app.handlers.load_post.append(discover_creators_handler)


def unregister():
    """Unregister the operators and menu."""

    pcoll = PREVIEW_COLLECTIONS.pop("avalon")
    bpy.utils.previews.remove(pcoll)
    bpy.types.TOPBAR_MT_editor_menus.remove(draw_avalon_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
