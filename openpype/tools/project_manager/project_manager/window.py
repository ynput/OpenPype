from Qt import QtWidgets, QtCore

from . import (
    ProjectModel,

    HierarchyModel,
    HierarchySelectionModel,
    HierarchyView
)

from avalon.api import AvalonMongoDB


class Window(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        dbcon = AvalonMongoDB()

        # TOP Project selection
        project_widget = QtWidgets.QWidget(self)

        project_model = ProjectModel(dbcon)

        project_combobox = QtWidgets.QComboBox(project_widget)
        project_combobox.setModel(project_model)
        project_combobox.setRootModelIndex(QtCore.QModelIndex())

        refresh_projects_btn = QtWidgets.QPushButton("Refresh", project_widget)

        project_layout = QtWidgets.QHBoxLayout(project_widget)
        project_layout.setContentsMargins(0, 0, 0, 0)
        project_layout.addWidget(refresh_projects_btn, 0)
        project_layout.addWidget(project_combobox, 0)
        project_layout.addStretch(1)

        hierarchy_model = HierarchyModel(dbcon)

        hierarchy_view = HierarchyView(dbcon, hierarchy_model, self)
        hierarchy_view.setModel(hierarchy_model)

        _selection_model = HierarchySelectionModel(
            hierarchy_model.multiselection_column_indexes
        )
        _selection_model.setModel(hierarchy_view.model())
        hierarchy_view.setSelectionModel(_selection_model)

        header = hierarchy_view.header()
        header.setStretchLastSection(False)
        for idx in range(header.count()):
            logical_index = header.logicalIndex(idx)
            if idx == 0:
                header.setSectionResizeMode(
                    logical_index, QtWidgets.QHeaderView.Stretch
                )
            else:
                header.setSectionResizeMode(
                    logical_index, QtWidgets.QHeaderView.ResizeToContents
                )

        buttons_widget = QtWidgets.QWidget(self)

        message_label = QtWidgets.QLabel(buttons_widget)
        save_btn = QtWidgets.QPushButton("Save", buttons_widget)

        buttons_layout = QtWidgets.QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addWidget(message_label)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(save_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(project_widget)
        main_layout.addWidget(hierarchy_view)
        main_layout.addWidget(buttons_widget)

        refresh_projects_btn.clicked.connect(self._on_project_refresh)
        project_combobox.currentIndexChanged.connect(self._on_project_change)
        save_btn.clicked.connect(self._on_save_click)

        self.project_model = project_model
        self.project_combobox = project_combobox

        self.hierarchy_view = hierarchy_view
        self.hierarchy_model = hierarchy_model

        self.message_label = message_label

        self.resize(1200, 600)

        self.refresh_projects()

    def _set_project(self, project_name=None):
        self.hierarchy_view.set_project(project_name)

    def refresh_projects(self):
        current_project = None
        if self.project_combobox.count() > 0:
            current_project = self.project_combobox.currentText()

        self.project_model.refresh()

        if self.project_combobox.count() == 0:
            return self._set_project()

        if current_project:
            row = self.project_combobox.findText(current_project)
            if row >= 0:
                self.project_combobox.setCurrentIndex(row)

        self._set_project(self.project_combobox.currentText())

    def _on_project_change(self):
        self._set_project(self.project_combobox.currentText())

    def _on_project_refresh(self):
        self.refresh_projects()

    def _on_save_click(self):
        self.hierarchy_model.save()

    def show_message(self, message):
        # TODO add nicer message pop
        self.message_label.setText(message)
