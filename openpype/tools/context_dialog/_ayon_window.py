import os
import json

import ayon_api
from qtpy import QtWidgets, QtCore, QtGui

from openpype import style
from openpype.lib.events import QueuedEventSystem
from openpype.tools.ayon_utils.models import (
    ProjectsModel,
    HierarchyModel,
)
from openpype.tools.ayon_utils.widgets import (
    ProjectsCombobox,
    FoldersWidget,
    TasksWidget,
)
from openpype.tools.utils.lib import (
    center_window,
    get_openpype_qt_app,
)


class SelectionModel(object):
    """Model handling selection changes.

    Triggering events:
    - "selection.project.changed"
    - "selection.folder.changed"
    - "selection.task.changed"
    """

    event_source = "selection.model"

    def __init__(self, controller):
        self._controller = controller

        self._project_name = None
        self._folder_id = None
        self._task_id = None
        self._task_name = None

    def get_selected_project_name(self):
        return self._project_name

    def set_selected_project(self, project_name):
        self._project_name = project_name
        self._controller.emit_event(
            "selection.project.changed",
            {"project_name": project_name},
            self.event_source
        )

    def get_selected_folder_id(self):
        return self._folder_id

    def set_selected_folder(self, folder_id):
        if folder_id == self._folder_id:
            return
        self._folder_id = folder_id
        self._controller.emit_event(
            "selection.folder.changed",
            {
                "project_name": self._project_name,
                "folder_id": folder_id,
            },
            self.event_source
        )

    def get_selected_task_name(self):
        return self._task_name

    def get_selected_task_id(self):
        return self._task_id

    def set_selected_task(self, task_id, task_name):
        if task_id == self._task_id:
            return

        self._task_name = task_name
        self._task_id = task_id
        self._controller.emit_event(
            "selection.task.changed",
            {
                "project_name": self._project_name,
                "folder_id": self._folder_id,
                "task_name": task_name,
                "task_id": task_id,
            },
            self.event_source
        )


class ExpectedSelection:
    def __init__(self, controller):
        self._project_name = None
        self._folder_id = None

        self._project_selected = True
        self._folder_selected = True

        self._controller = controller

    def _emit_change(self):
        self._controller.emit_event(
            "expected_selection_changed",
            self.get_expected_selection_data(),
        )

    def set_expected_selection(self, project_name, folder_id):
        self._project_name = project_name
        self._folder_id = folder_id

        self._project_selected = False
        self._folder_selected = False
        self._emit_change()

    def get_expected_selection_data(self):
        project_current = False
        folder_current = False
        if not self._project_selected:
            project_current = True
        elif not self._folder_selected:
            folder_current = True
        return {
            "project": {
                "name": self._project_name,
                "current": project_current,
                "selected": self._project_selected,
            },
            "folder": {
                "id": self._folder_id,
                "current": folder_current,
                "selected": self._folder_selected,
            },
        }

    def is_expected_project_selected(self, project_name):
        return project_name == self._project_name and self._project_selected

    def is_expected_folder_selected(self, folder_id):
        return folder_id == self._folder_id and self._folder_selected

    def expected_project_selected(self, project_name):
        if project_name != self._project_name:
            return False
        self._project_selected = True
        self._emit_change()
        return True

    def expected_folder_selected(self, folder_id):
        if folder_id != self._folder_id:
            return False
        self._folder_selected = True
        self._emit_change()
        return True


class ContextDialogController:
    def __init__(self):
        self._event_system = None

        self._projects_model = ProjectsModel(self)
        self._hierarchy_model = HierarchyModel(self)
        self._selection_model = SelectionModel(self)
        self._expected_selection = ExpectedSelection(self)

        self._confirmed = False
        self._is_strict = False
        self._output_path = None

        self._initial_project_name = None
        self._initial_folder_id = None
        self._initial_folder_label = None
        self._initial_project_found = True
        self._initial_folder_found = True
        self._initial_tasks_found = True

    def reset(self):
        self._emit_event("controller.reset.started")

        self._confirmed = False
        self._output_path = None

        self._initial_project_name = None
        self._initial_folder_id = None
        self._initial_folder_label = None
        self._initial_project_found = True
        self._initial_folder_found = True
        self._initial_tasks_found = True

        self._projects_model.reset()
        self._hierarchy_model.reset()

        self._emit_event("controller.reset.finished")

    def refresh(self):
        self._emit_event("controller.refresh.started")

        self._projects_model.reset()
        self._hierarchy_model.reset()

        self._emit_event("controller.refresh.finished")

    # Event handling
    def emit_event(self, topic, data=None, source=None):
        """Use implemented event system to trigger event."""

        if data is None:
            data = {}
        self._get_event_system().emit(topic, data, source)

    def register_event_callback(self, topic, callback):
        self._get_event_system().add_callback(topic, callback)

    def set_output_json_path(self, output_path):
        self._output_path = output_path

    def is_strict(self):
        return self._is_strict

    def set_strict(self, enabled):
        if self._is_strict is enabled:
            return
        self._is_strict = enabled
        self._emit_event("strict.changed", {"strict": enabled})

    # Data model functions
    def get_project_items(self, sender=None):
        return self._projects_model.get_project_items(sender)

    def get_folder_items(self, project_name, sender=None):
        return self._hierarchy_model.get_folder_items(project_name, sender)

    def get_task_items(self, project_name, folder_id, sender=None):
        return self._hierarchy_model.get_task_items(
            project_name, folder_id, sender
        )

    # Expected selection helpers
    def set_expected_selection(self, project_name, folder_id):
        return self._expected_selection.set_expected_selection(
            project_name, folder_id
        )

    def get_expected_selection_data(self):
        return self._expected_selection.get_expected_selection_data()

    def expected_project_selected(self, project_name):
        self._expected_selection.expected_project_selected(project_name)

    def expected_folder_selected(self, folder_id):
        self._expected_selection.expected_folder_selected(folder_id)

    # Selection handling
    def get_selected_project_name(self):
        return self._selection_model.get_selected_project_name()

    def set_selected_project(self, project_name):
        self._selection_model.set_selected_project(project_name)

    def get_selected_folder_id(self):
        return self._selection_model.get_selected_folder_id()

    def set_selected_folder(self, folder_id):
        self._selection_model.set_selected_folder(folder_id)

    def get_selected_task_name(self):
        return self._selection_model.get_selected_task_name()

    def get_selected_task_id(self):
        return self._selection_model.get_selected_task_id()

    def set_selected_task(self, task_id, task_name):
        self._selection_model.set_selected_task(task_id, task_name)

    def is_initial_context_valid(self):
        return self._initial_folder_found and self._initial_project_found

    def set_initial_context(self, project_name=None, asset_name=None):
        result = self._prepare_initial_context(project_name, asset_name)

        self._initial_project_name = project_name
        self._initial_folder_id = result["folder_id"]
        self._initial_folder_label = result["folder_label"]
        self._initial_project_found = result["project_found"]
        self._initial_folder_found = result["folder_found"]
        self._initial_tasks_found = result["tasks_found"]
        self._emit_event(
            "initial.context.changed",
            self.get_initial_context()
        )

    def get_initial_context(self):
        return {
            "project_name": self._initial_project_name,
            "folder_id": self._initial_folder_id,
            "folder_label": self._initial_folder_label,
            "project_found": self._initial_project_found,
            "folder_found": self._initial_folder_found,
            "tasks_found": self._initial_tasks_found,
            "valid": (
                self._initial_project_found
                and self._initial_folder_found
                and self._initial_tasks_found
            )
        }

    # Result of this tool
    def get_selected_context(self):
        project_name = None
        folder_id = None
        task_id = None
        task_name = None
        folder_path = None
        folder_name = None
        if self._confirmed:
            project_name = self.get_selected_project_name()
            folder_id = self.get_selected_folder_id()
            task_id = self.get_selected_task_id()
            task_name = self.get_selected_task_name()

        folder_item = None
        if folder_id:
            folder_item = self._hierarchy_model.get_folder_item(
                project_name, folder_id)

        if folder_item:
            folder_path = folder_item.path
            folder_name = folder_item.name
        return {
            "project": project_name,
            "project_name": project_name,
            "asset": folder_name,
            "folder_id": folder_id,
            "folder_path": folder_path,
            "task": task_name,
            "task_name": task_name,
            "task_id": task_id,
            "initial_context_valid": self.is_initial_context_valid(),
        }

    def confirm_selection(self):
        self._confirmed = True

    def store_output(self):
        if not self._output_path:
            return

        dirpath = os.path.dirname(self._output_path)
        os.makedirs(dirpath, exist_ok=True)
        with open(self._output_path, "w") as stream:
            json.dump(self.get_selected_context(), stream, indent=4)

    def _prepare_initial_context(self, project_name, asset_name):
        project_found = True
        output = {
            "project_found": project_found,
            "folder_id": None,
            "folder_label": None,
            "folder_found": True,
            "tasks_found": True,
        }
        if project_name is None:
            asset_name = None
        else:
            project = ayon_api.get_project(project_name)
            project_found = project is not None
        output["project_found"] = project_found
        if not project_found or not asset_name:
            return output

        output["folder_label"] = asset_name

        folder_id = None
        folder_found = False
        # First try to find by path
        folder = ayon_api.get_folder_by_path(project_name, asset_name)
        # Try to find by name if folder was not found by path
        #   - prevent to query by name if 'asset_name' contains '/'
        if not folder and "/" not in asset_name:
            folder = next(
                ayon_api.get_folders(
                    project_name, folder_names=[asset_name], fields=["id"]),
                None
            )

        if folder:
            folder_id = folder["id"]
            folder_found = True

        output["folder_id"] = folder_id
        output["folder_found"] = folder_found
        if not folder_found:
            return output

        tasks = list(ayon_api.get_tasks(
            project_name, folder_ids=[folder_id], fields=["id"]
        ))
        output["tasks_found"] = bool(tasks)
        return output

    def _get_event_system(self):
        """Inner event system for workfiles tool controller.

        Is used for communication with UI. Event system is created on demand.

        Returns:
            QueuedEventSystem: Event system which can trigger callbacks
                for topics.
        """

        if self._event_system is None:
            self._event_system = QueuedEventSystem()
        return self._event_system

    def _emit_event(self, topic, data=None):
        self.emit_event(topic, data, "controller")


class InvalidContextOverlay(QtWidgets.QFrame):
    confirmed = QtCore.Signal()

    def __init__(self, parent):
        super(InvalidContextOverlay, self).__init__(parent)
        self.setObjectName("OverlayFrame")

        mid_widget = QtWidgets.QWidget(self)
        label_widget = QtWidgets.QLabel(
            "Requested context was not found...",
            mid_widget
        )

        confirm_btn = QtWidgets.QPushButton("Close", mid_widget)

        mid_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        mid_layout = QtWidgets.QVBoxLayout(mid_widget)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.addWidget(label_widget, 0)
        mid_layout.addSpacing(30)
        mid_layout.addWidget(confirm_btn, 0)

        main_layout = QtWidgets.QGridLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(mid_widget, 1, 1)
        main_layout.setRowStretch(0, 1)
        main_layout.setRowStretch(1, 0)
        main_layout.setRowStretch(2, 1)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 0)
        main_layout.setColumnStretch(2, 1)

        confirm_btn.clicked.connect(self.confirmed)

        self._label_widget = label_widget
        self._confirm_btn = confirm_btn

    def set_context(
        self,
        project_name,
        folder_label,
        project_found,
        folder_found,
        tasks_found,
    ):
        lines = []
        if not project_found:
            lines.extend([
                "Requested project '{}' was not found...".format(
                    project_name),
            ])

        elif not folder_found:
            lines.extend([
                "Requested folder was not found...",
                "",
                "Project: {}".format(project_name),
                "Folder: {}".format(folder_label),
            ])
        elif not tasks_found:
            lines.extend([
                "Requested folder does not have any tasks...",
                "",
                "Project: {}".format(project_name),
                "Folder: {}".format(folder_label),
            ])
        else:
            lines.append("Requested context was not found...")
        self._label_widget.setText("<br/>".join(lines))


class ContextDialog(QtWidgets.QDialog):
    """Dialog to select a context.

    Context has 3 parts:
    - Project
    - Asset
    - Task

    It is possible to predefine project and asset. In that case their widgets
    will have passed preselected values and will be disabled.
    """
    def __init__(self, controller=None, parent=None):
        super(ContextDialog, self).__init__(parent)

        self.setWindowTitle("Select Context")
        self.setWindowIcon(QtGui.QIcon(style.app_icon_path()))

        if controller is None:
            controller = ContextDialogController()

        # Enable minimize and maximize for app
        window_flags = QtCore.Qt.Window
        if not parent:
            window_flags |= QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(window_flags)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        # UI initialization
        main_splitter = QtWidgets.QSplitter(self)

        # Left side widget contains project combobox and asset widget
        left_side_widget = QtWidgets.QWidget(main_splitter)

        project_combobox = ProjectsCombobox(
            controller,
            parent=left_side_widget,
            handle_expected_selection=True
        )
        project_combobox.set_select_item_visible(True)

        # Assets widget
        folders_widget = FoldersWidget(
            controller,
            parent=left_side_widget,
            handle_expected_selection=True
        )

        left_side_layout = QtWidgets.QVBoxLayout(left_side_widget)
        left_side_layout.setContentsMargins(0, 0, 0, 0)
        left_side_layout.addWidget(project_combobox, 0)
        left_side_layout.addWidget(folders_widget, 1)

        # Right side of window contains only tasks
        tasks_widget = TasksWidget(controller, parent=main_splitter)

        # Add widgets to main splitter
        main_splitter.addWidget(left_side_widget)
        main_splitter.addWidget(tasks_widget)

        # Set stretch of both sides
        main_splitter.setStretchFactor(0, 7)
        main_splitter.setStretchFactor(1, 3)

        # Add confimation button to bottom right
        ok_btn = QtWidgets.QPushButton("OK", self)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(ok_btn, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(main_splitter, 1)
        main_layout.addLayout(buttons_layout, 0)

        overlay_widget = InvalidContextOverlay(self)
        overlay_widget.setVisible(False)

        ok_btn.clicked.connect(self._on_ok_click)
        project_combobox.refreshed.connect(self._on_projects_refresh)
        overlay_widget.confirmed.connect(self._on_overlay_confirm)

        controller.register_event_callback(
            "selection.project.changed",
            self._on_project_selection_change
        )
        controller.register_event_callback(
            "selection.folder.changed",
            self._on_folder_selection_change
        )
        controller.register_event_callback(
            "selection.task.changed",
            self._on_task_selection_change
        )
        controller.register_event_callback(
            "initial.context.changed",
            self._on_init_context_change
        )
        controller.register_event_callback(
            "strict.changed",
            self._on_strict_changed
        )
        controller.register_event_callback(
            "controller.reset.finished",
            self._on_controller_reset
        )
        controller.register_event_callback(
            "controller.refresh.finished",
            self._on_controller_refresh
        )

        # Set stylehseet and resize window on first show
        self._first_show = True
        self._visible = False

        self._controller = controller

        self._project_combobox = project_combobox
        self._folders_widget = folders_widget
        self._tasks_widget = tasks_widget

        self._ok_btn = ok_btn

        self._overlay_widget = overlay_widget

        self._apply_strict_changes(self.is_strict())

    def is_strict(self):
        return self._controller.is_strict()

    def showEvent(self, event):
        """Override show event to do some callbacks."""
        super(ContextDialog, self).showEvent(event)
        self._visible = True

        if self._first_show:
            self._first_show = False
            # Set stylesheet and resize
            self.setStyleSheet(style.load_stylesheet())
            self.resize(600, 700)
            center_window(self)
        self._controller.refresh()

        initial_context = self._controller.get_initial_context()
        self._set_init_context(initial_context)
        self._overlay_widget.resize(self.size())

    def resizeEvent(self, event):
        super(ContextDialog, self).resizeEvent(event)
        self._overlay_widget.resize(self.size())

    def closeEvent(self, event):
        """Ignore close event if is in strict state and context is not done."""
        if self.is_strict() and not self._ok_btn.isEnabled():
            # Allow to close window when initial context is not valid
            if self._controller.is_initial_context_valid():
                event.ignore()
                return

        if self.is_strict():
            self._confirm_selection()
        self._visible = False
        super(ContextDialog, self).closeEvent(event)

    def set_strict(self, enabled):
        """Change strictness of dialog."""

        self._controller.set_strict(enabled)

    def refresh(self):
        """Refresh all widget one by one.

        When asset refresh is triggered we have to wait when is done so
        this method continues with `_on_asset_widget_refresh_finished`.
        """

        self._controller.reset()

    def get_context(self):
        """Result of dialog."""
        return self._controller.get_selected_context()

    def set_context(self, project_name=None, asset_name=None):
        """Set context which will be used and locked in dialog."""

        self._controller.set_initial_context(project_name, asset_name)

    def _on_projects_refresh(self):
        initial_context = self._controller.get_initial_context()
        self._controller.set_expected_selection(
            initial_context["project_name"],
            initial_context["folder_id"]
        )

    def _on_overlay_confirm(self):
        self.close()

    def _on_ok_click(self):
        # Store values to output
        self._confirm_selection()
        # Close dialog
        self.accept()

    def _confirm_selection(self):
        self._controller.confirm_selection()

    def _on_project_selection_change(self, event):
        self._on_selection_change(
            event["project_name"],
        )

    def _on_folder_selection_change(self, event):
        self._on_selection_change(
            event["project_name"],
            event["folder_id"],
        )

    def _on_task_selection_change(self, event):
        self._on_selection_change(
            event["project_name"],
            event["folder_id"],
            event["task_name"],
        )

    def _on_selection_change(
        self, project_name, folder_id=None, task_name=None
    ):
        self._validate_strict(project_name, folder_id, task_name)

    def _on_init_context_change(self, event):
        self._set_init_context(event.data)
        if self._visible:
            self._controller.set_expected_selection(
                event["project_name"], event["folder_id"]
            )

    def _set_init_context(self, init_context):
        project_name = init_context["project_name"]
        if not init_context["valid"]:
            self._overlay_widget.setVisible(True)
            self._overlay_widget.set_context(
                project_name,
                init_context["folder_label"],
                init_context["project_found"],
                init_context["folder_found"],
                init_context["tasks_found"]
            )
            return

        self._overlay_widget.setVisible(False)
        if project_name:
            self._project_combobox.setEnabled(False)
            if init_context["folder_id"]:
                self._folders_widget.setEnabled(False)
        else:
            self._project_combobox.setEnabled(True)
            self._folders_widget.setEnabled(True)

    def _on_strict_changed(self, event):
        self._apply_strict_changes(event["strict"])

    def _on_controller_reset(self):
        self._apply_strict_changes(self.is_strict())
        self._project_combobox.refresh()

    def _on_controller_refresh(self):
        self._project_combobox.refresh()

    def _apply_strict_changes(self, is_strict):
        if not is_strict:
            if not self._ok_btn.isEnabled():
                self._ok_btn.setEnabled(True)
            return
        context = self._controller.get_selected_context()
        self._validate_strict(
            context["project_name"],
            context["folder_id"],
            context["task_name"]
        )

    def _validate_strict(self, project_name, folder_id, task_name):
        if not self.is_strict():
            return

        enabled = True
        if not project_name or not folder_id or not task_name:
            enabled = False
        self._ok_btn.setEnabled(enabled)


def main(
    path_to_store,
    project_name=None,
    asset_name=None,
    strict=True
):
    # Run Qt application
    app = get_openpype_qt_app()
    controller = ContextDialogController()
    controller.set_strict(strict)
    controller.set_initial_context(project_name, asset_name)
    controller.set_output_json_path(path_to_store)
    window = ContextDialog(controller=controller)
    window.show()
    app.exec_()
    controller.store_output()
