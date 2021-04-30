from Qt import QtWidgets, QtCore

from . import (
    HierarchyModel,
    HierarchySelectionModel,
    HierarchyView
)

from avalon.api import AvalonMongoDB


class Window(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        dbcon = AvalonMongoDB()

        model = HierarchyModel(dbcon)
        view = HierarchyView(model, self)
        view.setModel(model)
        _selection_model = HierarchySelectionModel()
        _selection_model.setModel(view.model())
        view.setSelectionModel(_selection_model)

        header = view.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(
            header.logicalIndex(0), QtWidgets.QHeaderView.Stretch
        )
        checkbox = QtWidgets.QCheckBox(self)
        # btn = QtWidgets.QPushButton("Refresh")

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(view)
        main_layout.addWidget(checkbox)
        # main_layout.addWidget(btn)
        # btn.clicked.connect(self._on_refresh)

        checkbox.toggled.connect(self._on_checkbox)

        self.view = view
        self.model = model
        # self.btn = btn
        self.checkbox = checkbox

        self.change_edit_mode()

        self.resize(1200, 600)
        model.set_project({"name": "test"})

    def change_edit_mode(self, value=None):
        if value is None:
            value = self.checkbox.isChecked()
        self.model.change_edit_mode(value)

    def _on_checkbox(self, value):
        self.change_edit_mode(value)

    def _on_refresh(self):
        self.model.clear()
