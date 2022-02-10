import os
import json

from Qt import QtWidgets, QtCore, QtGui
from avalon.api import AvalonMongoDB

from openpype import style
from openpype.tools.utils.lib import center_window
from openpype.tools.utils.assets_widget import SingleSelectAssetsWidget
from openpype.tools.utils.constants import (
    PROJECT_NAME_ROLE
)
from openpype.tools.utils.tasks_widget import TasksWidget
from openpype.tools.utils.models import (
    ProjectModel,
    ProjectSortFilterProxy
)


class ContextDialog(QtWidgets.QDialog):
    """Dialog to select a context.

    Context has 3 parts:
    - Project
    - Aseet
    - Task

    It is possible to predefine project and asset. In that case their widgets
    will have passed preselected values and will be disabled.
    """
    def __init__(self, parent=None):
        super(ContextDialog, self).__init__(parent)

        self.setWindowTitle("Select Context")
        self.setWindowIcon(QtGui.QIcon(style.app_icon_path()))

        # Enable minimize and maximize for app
        window_flags = QtCore.Qt.Window
        if not parent:
            window_flags |= QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(window_flags)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        dbcon = AvalonMongoDB()

        # UI initialization
        main_splitter = QtWidgets.QSplitter(self)

        # Left side widget contains project combobox and asset widget
        left_side_widget = QtWidgets.QWidget(main_splitter)

        project_combobox = QtWidgets.QComboBox(left_side_widget)
        # Styled delegate to propagate stylessheet
        project_delegate = QtWidgets.QStyledItemDelegate(project_combobox)
        project_combobox.setItemDelegate(project_delegate)
        # Project model with only active projects without default item
        project_model = ProjectModel(
            dbcon,
            only_active=True,
            add_default_project=False
        )
        # Sorting proxy model
        project_proxy = ProjectSortFilterProxy()
        project_proxy.setSourceModel(project_model)
        project_combobox.setModel(project_proxy)

        # Assets widget
        assets_widget = SingleSelectAssetsWidget(
            dbcon, parent=left_side_widget
        )

        left_side_layout = QtWidgets.QVBoxLayout(left_side_widget)
        left_side_layout.setContentsMargins(0, 0, 0, 0)
        left_side_layout.addWidget(project_combobox)
        left_side_layout.addWidget(assets_widget)

        # Right side of window contains only tasks
        tasks_widget = TasksWidget(dbcon, main_splitter)

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

        # Timer which will trigger asset refresh
        # - this is needed because asset widget triggers
        #   finished refresh before hides spin box so we need to trigger
        #   refreshing in small offset if we want re-refresh asset widget
        assets_timer = QtCore.QTimer()
        assets_timer.setInterval(50)
        assets_timer.setSingleShot(True)

        assets_timer.timeout.connect(self._on_asset_refresh_timer)

        project_combobox.currentIndexChanged.connect(
            self._on_project_combo_change
        )
        assets_widget.selection_changed.connect(self._on_asset_change)
        assets_widget.refresh_triggered.connect(self._on_asset_refresh_trigger)
        assets_widget.refreshed.connect(self._on_asset_widget_refresh_finished)
        tasks_widget.task_changed.connect(self._on_task_change)
        ok_btn.clicked.connect(self._on_ok_click)

        self._dbcon = dbcon

        self._project_combobox = project_combobox
        self._project_model = project_model
        self._project_proxy = project_proxy
        self._project_delegate = project_delegate

        self._assets_widget = assets_widget

        self._tasks_widget = tasks_widget

        self._ok_btn = ok_btn

        self._strict = False

        # Values set by `set_context` method
        self._set_context_project = None
        self._set_context_asset = None

        # Requirements for asset widget refresh
        self._assets_timer = assets_timer
        self._rerefresh_assets = True
        self._assets_refreshing = False

        # Set stylehseet and resize window on first show
        self._first_show = True

        # Helper attributes for handling of refresh
        self._ignore_value_changes = False
        self._refresh_on_next_show = True

        # Output of dialog
        self._context_to_store = {
            "project": None,
            "asset": None,
            "task": None
        }

    def closeEvent(self, event):
        """Ignore close event if is in strict state and context is not done."""
        if self._strict and not self._ok_btn.isEnabled():
            event.ignore()
            return

        if self._strict:
            self._confirm_values()
        super(ContextDialog, self).closeEvent(event)

    def set_strict(self, strict):
        """Change strictness of dialog."""
        self._strict = strict
        self._validate_strict()

    def _set_refresh_on_next_show(self):
        """Refresh will be called on next showEvent.

        If window is already visible then just execute refresh.
        """
        self._refresh_on_next_show = True
        if self.isVisible():
            self.refresh()

    def _refresh_assets(self):
        """Trigger refreshing of asset widget.

        This will set mart to rerefresh asset when current refreshing is done
        or do it immidietely if asset widget is not refreshing at the time.
        """
        if self._assets_refreshing:
            self._rerefresh_assets = True
        else:
            self._on_asset_refresh_timer()

    def showEvent(self, event):
        """Override show event to do some callbacks."""
        super(ContextDialog, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            # Set stylesheet and resize
            self.setStyleSheet(style.load_stylesheet())
            self.resize(600, 700)
            center_window(self)

        if self._refresh_on_next_show:
            self.refresh()

    def refresh(self):
        """Refresh all widget one by one.

        When asset refresh is triggered we have to wait when is done so
        this method continues with `_on_asset_widget_refresh_finished`.
        """
        # Change state of refreshing (no matter how refresh was called)
        self._refresh_on_next_show = False

        # Ignore changes of combobox and asset widget
        self._ignore_value_changes = True

        # Get current project name to be able set it afterwards
        select_project_name = self._dbcon.Session.get("AVALON_PROJECT")
        # Trigger project refresh
        self._project_model.refresh()
        # Sort projects
        self._project_proxy.sort(0)

        # Disable combobox if project was passed to `set_context`
        if self._set_context_project:
            select_project_name = self._set_context_project
            self._project_combobox.setEnabled(False)
        else:
            # Find new project to select
            self._project_combobox.setEnabled(True)
            if (
                select_project_name is None
                and self._project_proxy.rowCount() > 0
            ):
                index = self._project_proxy.index(0, 0)
                select_project_name = index.data(PROJECT_NAME_ROLE)

        self._ignore_value_changes = False

        idx = self._project_combobox.findText(select_project_name)
        if idx >= 0:
            self._project_combobox.setCurrentIndex(idx)
        self._dbcon.Session["AVALON_PROJECT"] = (
            self._project_combobox.currentText()
        )

        # Trigger asset refresh
        self._refresh_assets()

    def _on_asset_refresh_timer(self):
        """This is only way how to trigger refresh asset widget.

        Use `_refresh_assets` method to refresh asset widget.
        """
        self._assets_widget.refresh()

    def _on_asset_widget_refresh_finished(self):
        """Catch when asset widget finished refreshing."""
        # If should refresh again then skip all other callbacks and trigger
        #   assets timer directly.
        self._assets_refreshing = False
        if self._rerefresh_assets:
            self._rerefresh_assets = False
            self._assets_timer.start()
            return

        self._ignore_value_changes = True
        if self._set_context_asset:
            self._dbcon.Session["AVALON_ASSET"] = self._set_context_asset
            self._assets_widget.setEnabled(False)
            self._assets_widget.select_assets(self._set_context_asset)
            self._set_asset_to_tasks_widget()
        else:
            self._assets_widget.setEnabled(True)
            self._assets_widget.set_current_asset_btn_visibility(False)

        # Refresh tasks
        self._tasks_widget.refresh()

        self._ignore_value_changes = False

        self._validate_strict()

    def _on_project_combo_change(self):
        if self._ignore_value_changes:
            return
        project_name = self._project_combobox.currentText()

        if self._dbcon.Session.get("AVALON_PROJECT") == project_name:
            return

        self._dbcon.Session["AVALON_PROJECT"] = project_name

        self._refresh_assets()
        self._validate_strict()

    def _on_asset_refresh_trigger(self):
        self._assets_refreshing = True
        self._on_asset_change()

    def _on_asset_change(self):
        """Selected assets have changed"""
        if self._ignore_value_changes:
            return
        self._set_asset_to_tasks_widget()

    def _on_task_change(self):
        self._validate_strict()

    def _set_asset_to_tasks_widget(self):
        # filter None docs they are silo
        asset_id = self._assets_widget.get_selected_asset_id()

        self._tasks_widget.set_asset_id(asset_id)

    def _confirm_values(self):
        """Store values to output."""
        self._context_to_store["project"] = self.get_selected_project()
        self._context_to_store["asset"] = self.get_selected_asset()
        self._context_to_store["task"] = self.get_selected_task()

    def _on_ok_click(self):
        # Store values to output
        self._confirm_values()
        # Close dialog
        self.accept()

    def get_selected_project(self):
        """Get selected project."""
        return self._project_combobox.currentText()

    def get_selected_asset(self):
        """Currently selected asset in asset widget."""
        return self._assets_widget.get_selected_asset_name()

    def get_selected_task(self):
        """Currently selected task."""
        return self._tasks_widget.get_selected_task_name()

    def _validate_strict(self):
        if not self._strict:
            if not self._ok_btn.isEnabled():
                self._ok_btn.setEnabled(True)
            return

        enabled = True
        if not self._set_context_project and not self.get_selected_project():
            enabled = False
        elif not self._set_context_asset and not self.get_selected_asset():
            enabled = False
        elif not self.get_selected_task():
            enabled = False
        self._ok_btn.setEnabled(enabled)

    def set_context(self, project_name=None, asset_name=None):
        """Set context which will be used and locked in dialog."""
        if project_name is None:
            asset_name = None

        self._set_context_project = project_name
        self._set_context_asset = asset_name

        self._context_to_store["project"] = project_name
        self._context_to_store["asset"] = asset_name

        self._set_refresh_on_next_show()

    def get_context(self):
        """Result of dialog."""
        return self._context_to_store


def main(
    path_to_store,
    project_name=None,
    asset_name=None,
    strict=True
):
    # Run Qt application
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    window = ContextDialog()
    window.set_strict(strict)
    window.set_context(project_name, asset_name)
    window.show()
    app.exec_()

    # Get result from window
    data = window.get_context()

    # Make sure json filepath directory exists
    file_dir = os.path.dirname(path_to_store)
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)

    # Store result into json file
    with open(path_to_store, "w") as stream:
        json.dump(data, stream)
