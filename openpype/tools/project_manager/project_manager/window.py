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

        project_model = ProjectModel(dbcon)

        project_combobox = QtWidgets.QComboBox()
        project_combobox.setModel(project_model)
        project_combobox.setRootModelIndex(QtCore.QModelIndex())

        hierarchy_model = HierarchyModel(dbcon)

        hierarchy_view = HierarchyView(hierarchy_model, self)
        hierarchy_view.setModel(hierarchy_model)
        _selection_model = HierarchySelectionModel()
        _selection_model.setModel(hierarchy_view.model())
        hierarchy_view.setSelectionModel(_selection_model)

        header = hierarchy_view.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(
            header.logicalIndex(0), QtWidgets.QHeaderView.Stretch
        )
        checkbox = QtWidgets.QCheckBox(self)
        # btn = QtWidgets.QPushButton("Refresh")

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(project_combobox)
        main_layout.addWidget(hierarchy_view)
        main_layout.addWidget(checkbox)
        # main_layout.addWidget(btn)
        # btn.clicked.connect(self._on_refresh)

        checkbox.toggled.connect(self._on_checkbox)

        # self.btn = btn
        self.hierarchy_view = hierarchy_view
        self.hierarchy_model = hierarchy_model
        self.checkbox = checkbox

        self.change_edit_mode()

        self.resize(1200, 600)

        self.refresh_projects()

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
                self._set_project(current_project)
                index = self.project_combobox.model().index(row, 0)
                self.project_combobox.setCurrentIndex(index)
                return

        self._set_project(self.project_combobox.currentText())

    def _set_project(self, project_name=None):
        self.hierarchy_model.set_project(project_name)

    def change_edit_mode(self, value=None):
        if value is None:
            value = self.checkbox.isChecked()
        self.hierarchy_model.change_edit_mode(value)

    def _on_checkbox(self, value):
        self.change_edit_mode(value)

    def _on_refresh(self):
        self.model.clear()
