import os
import json

from Qt import QtWidgets, QtCore, QtGui
from avalon.api import AvalonMongoDB

from openpype import style
from openpype.tools.utils.widgets import AssetWidget
from openpype.tools.utils.constants import (
    TASK_NAME_ROLE,
    PROJECT_NAME_ROLE
)
from openpype.tools.utils.models import (
    ProjectModel,
    ProjectSortFilterProxy,
    TasksModel,
    TasksProxyModel
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

        left_side_widget = QtWidgets.QWidget(main_splitter)

        project_combobox = QtWidgets.QComboBox(left_side_widget)
        project_delegate = QtWidgets.QStyledItemDelegate(project_combobox)
        project_combobox.setItemDelegate(project_delegate)
        project_model = ProjectModel(
            dbcon,
            only_active=True,
            add_default_project=False
        )
        project_proxy = ProjectSortFilterProxy()
        project_proxy.setSourceModel(project_model)
        project_combobox.setModel(project_proxy)

        # Assets widget
        assets_widget = AssetWidget(
            dbcon, multiselection=False, parent=left_side_widget
        )

        left_side_layout = QtWidgets.QVBoxLayout(left_side_widget)
        left_side_layout.setContentsMargins(0, 0, 0, 0)
        left_side_layout.addWidget(project_combobox)
        left_side_layout.addWidget(assets_widget)

        task_view = QtWidgets.QListView(main_splitter)
        task_model = TasksModel(dbcon)
        task_proxy = TasksProxyModel()
        task_proxy.setSourceModel(task_model)
        task_view.setModel(task_proxy)

        main_splitter.addWidget(left_side_widget)
        main_splitter.addWidget(task_view)
        main_splitter.setStretchFactor(0, 7)
        main_splitter.setStretchFactor(1, 3)

        ok_btn = QtWidgets.QPushButton("OK", self)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(ok_btn, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(main_splitter, 1)
        main_layout.addLayout(buttons_layout, 0)

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
        task_view.selectionModel().selectionChanged.connect(
            self._on_task_change
        )
        ok_btn.clicked.connect(self._on_ok_click)

        self._dbcon = dbcon

        self._project_combobox = project_combobox
        self._project_model = project_model
        self._project_proxy = project_proxy
        self._project_delegate = project_delegate

        self._assets_widget = assets_widget

        self._task_view = task_view
        self._task_model = task_model
        self._task_proxy = task_proxy

        self._ok_btn = ok_btn

        self._strict = False

        # Values set by `set_context` method
        self._set_context_project = None
        self._set_context_asset = None

        # Requirements for asset widget refresh
        self._assets_timer = assets_timer
        self._rerefresh_assets = True
        self._assets_refreshing = False

        # Helper attributes for handling of refresh
        self._ignore_value_changes = False
        self._first_show = True
        self._refresh_on_next_show = True

        # Output of dialog
        self._context_to_store = {
            "project": None,
            "asset": None,
            "task": None
        }

    def closeEvent(self, event):
        if self._strict and not self._ok_btn.isEnabled():
            event.ignore()
            return

        if self._strict:
            self._confirm_values()
        super(ContextDialog, self).closeEvent(event)

    def set_strict(self, strict):
        self._strict = strict
        self._validate_strict()

    def _set_refresh_on_next_show(self):
        if self._refresh_on_next_show:
            return

        self._refresh_on_next_show = True
        if self.isVisible():
            self.refresh()

    def _refresh_assets(self):
        if self._assets_refreshing:
            self._rerefresh_assets = True
        else:
            self._on_asset_refresh_timer()

    def showEvent(self, event):
        super(ContextDialog, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.setStyleSheet(style.load_stylesheet())
            self.resize(600, 700)

        if self._refresh_on_next_show:
            self.refresh()

    def refresh(self):
        """Load assets from database"""
        self._refresh_on_next_show = False

        self._ignore_value_changes = True

        select_project_name = self._dbcon.Session.get("AVALON_PROJECT")
        self._project_model.refresh()
        self._project_proxy.sort(0)

        if self._set_context_project:
            select_project_name = self._set_context_project
            self._project_combobox.setEnabled(False)
        else:
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

        self._refresh_assets()

    def _on_asset_refresh_timer(self):
        self._assets_widget.refresh()

    def _on_asset_widget_refresh_finished(self):
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
            self._set_asset_to_task_model()
        else:
            self._assets_widget.setEnabled(True)
            self._assets_widget.set_current_asset_btn_visibility(False)

        self._task_model.refresh()
        self._task_proxy.sort(0, QtCore.Qt.AscendingOrder)

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
        self._set_asset_to_task_model()

    def _on_task_change(self):
        self._validate_strict()

    def _set_asset_to_task_model(self):
        # filter None docs they are silo
        asset_docs = self._assets_widget.get_selected_assets()
        asset_ids = [asset_doc["_id"] for asset_doc in asset_docs]
        asset_id = None
        if asset_ids:
            asset_id = asset_ids[0]
        self._task_model.set_asset_id(asset_id)

    def _confirm_values(self):
        self._context_to_store["project"] = self.get_selected_project()
        self._context_to_store["asset"] = self.get_selected_asset()
        self._context_to_store["task"] = self.get_selected_task()

    def _on_ok_click(self):
        self._confirm_values()
        self.accept()

    def get_selected_project(self):
        return self._project_combobox.currentText()

    def get_selected_asset(self):
        asset_name = None
        for asset_doc in self._assets_widget.get_selected_assets():
            asset_name = asset_doc["name"]
            break
        return asset_name

    def get_selected_task(self):
        task_name = None
        index = self._task_view.selectionModel().currentIndex()
        if index.isValid():
            task_name = index.data(TASK_NAME_ROLE)
        return task_name

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
        if project_name is None:
            asset_name = None

        self._set_context_project = project_name
        self._set_context_asset = asset_name

        self._context_to_store["project"] = project_name
        self._context_to_store["asset"] = asset_name

        self._set_refresh_on_next_show()

    def get_context(self):
        return self._context_to_store


def main(
    path_to_store,
    project_name=None,
    asset_name=None,
    strict=True
):
    app = QtWidgets.QApplication([])
    window = ContextDialog()
    window.set_strict(strict)
    window.set_context(project_name, asset_name)
    window.show()
    app.exec_()

    data = window.get_context()

    file_dir = os.path.dirname(path_to_store)
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)

    with open(path_to_store, "w") as stream:
        json.dump(data, stream)
