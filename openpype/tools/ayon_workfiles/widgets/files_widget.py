from qtpy import QtWidgets, QtGui, QtCore


class FilesModel(QtGui.QStandardItemModel):
    """A model for displaying files."""

    def __init__(self, control):
        super(FilesModel, self).__init__()

        self._last_project_name = None
        self._last_folder_id = None
        self._last_task_name = None

        self._control = control


class FilesWidget(QtWidgets.QWidget):
    """A widget displaying files that allows to save and open files."""

    file_opened = QtCore.Signal()

    def __init__(self, control, parent):
        super(FilesWidget, self).__init__(parent)

        view = QtWidgets.QTreeView(self)

        file_model = FilesModel(control)
        file_proxy_model = QtCore.QSortFilterProxyModel()
        file_proxy_model.setSourceModel(file_model)

        view.setModel(file_proxy_model)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(view, 1)
