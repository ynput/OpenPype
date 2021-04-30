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

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(project_widget)
        main_layout.addWidget(hierarchy_view)

        refresh_projects_btn.clicked.connect(self._on_project_refresh)
        project_combobox.currentIndexChanged.connect(self._on_project_change)

        self.project_model = project_model
        self.project_combobox = project_combobox

        self.hierarchy_view = hierarchy_view
        self.hierarchy_model = hierarchy_model

        self.resize(1200, 600)

        self.refresh_projects()

    def _set_project(self, project_name=None):
        self.hierarchy_model.set_project(project_name)

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
