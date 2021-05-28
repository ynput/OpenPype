from Qt import QtWidgets, QtCore, QtGui

from . import (
    ProjectModel,

    HierarchyModel,
    HierarchySelectionModel,
    HierarchyView,

    CreateProjectDialog
)
from .style import load_stylesheet, ResourceCache

from openpype import resources
from avalon.api import AvalonMongoDB


class ProjectManagerWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ProjectManagerWindow, self).__init__(parent)

        self.setWindowTitle("OpenPype Project Manager")
        self.setWindowIcon(QtGui.QIcon(resources.pype_icon_filepath()))

        # Top part of window
        top_part_widget = QtWidgets.QWidget(self)

        # Project selection
        project_widget = QtWidgets.QWidget(top_part_widget)

        dbcon = AvalonMongoDB()

        project_model = ProjectModel(dbcon)
        project_combobox = QtWidgets.QComboBox(project_widget)
        project_combobox.setModel(project_model)
        project_combobox.setRootModelIndex(QtCore.QModelIndex())
        style_delegate = QtWidgets.QStyledItemDelegate()
        project_combobox.setItemDelegate(style_delegate)

        refresh_projects_btn = QtWidgets.QPushButton(project_widget)
        refresh_projects_btn.setIcon(ResourceCache.get_icon("refresh"))
        refresh_projects_btn.setToolTip("Refresh projects")
        refresh_projects_btn.setObjectName("IconBtn")

        create_project_btn = QtWidgets.QPushButton(
            "Create project...", project_widget
        )

        project_layout = QtWidgets.QHBoxLayout(project_widget)
        project_layout.setContentsMargins(0, 0, 0, 0)
        project_layout.addWidget(project_combobox, 0)
        project_layout.addWidget(refresh_projects_btn, 0)
        project_layout.addWidget(create_project_btn, 0)
        project_layout.addStretch(1)

        # Helper buttons
        helper_btns_widget = QtWidgets.QWidget(top_part_widget)

        helper_label = QtWidgets.QLabel("Add:", helper_btns_widget)
        add_asset_btn = QtWidgets.QPushButton(
            ResourceCache.get_icon("asset", "default"),
            "Asset",
            helper_btns_widget
        )
        add_task_btn = QtWidgets.QPushButton(
            ResourceCache.get_icon("task", "default"),
            "Task",
            helper_btns_widget
        )

        helper_btns_layout = QtWidgets.QHBoxLayout(helper_btns_widget)
        helper_btns_layout.setContentsMargins(0, 0, 0, 0)
        helper_btns_layout.addWidget(helper_label)
        helper_btns_layout.addWidget(add_asset_btn)
        helper_btns_layout.addWidget(add_task_btn)
        helper_btns_layout.addStretch(1)

        # Add widgets to top widget layout
        top_part_layout = QtWidgets.QVBoxLayout(top_part_widget)
        top_part_layout.setContentsMargins(0, 0, 0, 0)
        top_part_layout.addWidget(project_widget)
        top_part_layout.addWidget(helper_btns_widget)

        hierarchy_model = HierarchyModel(dbcon)

        hierarchy_view = HierarchyView(dbcon, hierarchy_model, self)
        hierarchy_view.setModel(hierarchy_model)

        _selection_model = HierarchySelectionModel(
            hierarchy_model.multiselection_column_indexes
        )
        _selection_model.setModel(hierarchy_view.model())
        hierarchy_view.setSelectionModel(_selection_model)

        buttons_widget = QtWidgets.QWidget(self)

        message_label = QtWidgets.QLabel(buttons_widget)
        save_btn = QtWidgets.QPushButton("Save", buttons_widget)

        buttons_layout = QtWidgets.QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addWidget(message_label)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(save_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(top_part_widget)
        main_layout.addWidget(hierarchy_view)
        main_layout.addWidget(buttons_widget)

        refresh_projects_btn.clicked.connect(self._on_project_refresh)
        create_project_btn.clicked.connect(self._on_project_create)
        project_combobox.currentIndexChanged.connect(self._on_project_change)
        save_btn.clicked.connect(self._on_save_click)
        add_asset_btn.clicked.connect(self._on_add_asset)
        add_task_btn.clicked.connect(self._on_add_task)

        self.project_model = project_model
        self.project_combobox = project_combobox

        self.hierarchy_view = hierarchy_view
        self.hierarchy_model = hierarchy_model

        self.message_label = message_label

        self.resize(1200, 600)
        self.setStyleSheet(load_stylesheet())

        self.refresh_projects()

    def _set_project(self, project_name=None):
        self.hierarchy_view.set_project(project_name)

    def refresh_projects(self, project_name=None):
        if project_name is None:
            if self.project_combobox.count() > 0:
                project_name = self.project_combobox.currentText()

        self.project_model.refresh()

        if self.project_combobox.count() == 0:
            return self._set_project()

        if project_name:
            row = self.project_combobox.findText(project_name)
            if row >= 0:
                self.project_combobox.setCurrentIndex(row)

        self._set_project(self.project_combobox.currentText())

    def _on_project_change(self):
        self._set_project(self.project_combobox.currentText())

    def _on_project_refresh(self):
        self.refresh_projects()

    def _on_save_click(self):
        self.hierarchy_model.save()

    def _on_add_asset(self):
        self.hierarchy_view.add_asset()

    def _on_add_task(self):
        self.hierarchy_view.add_task()

    def show_message(self, message):
        # TODO add nicer message pop
        self.message_label.setText(message)

    def _on_project_create(self):
        dialog = CreateProjectDialog(self)
        dialog.exec_()
        if dialog.result() != 1:
            return

        project_name = dialog.project_name
        self.show_message("Created project \"{}\"".format(project_name))
        self.refresh_projects(project_name)
