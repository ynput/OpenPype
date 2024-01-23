from qtpy import QtCore, QtGui


class BatchPublisherModel(QtCore.QAbstractTableModel):
    HEADER_LABELS = [
        str(),
        "Filepath",
        "Folder (Asset)",
        "Task",
        "Product Type (Family)",
        "Product Name (subset)",
        "Representation",
        "Version"]
    COLUMN_OF_CHECKBOX = 0
    COLUMN_OF_DIRECTORY = 1
    COLUMN_OF_FOLDER = 2
    COLUMN_OF_TASK = 3
    COLUMN_OF_PRODUCT_TYPE = 4
    COLUMN_OF_PRODUCT_NAME = 5
    COLUMN_OF_REPRESENTATION = 6
    COLUMN_OF_VERSION = 7

    def __init__(self, controller):
        super(BatchPublisherModel, self).__init__()

        self._controller = controller
        self._ingest_files = []

    def set_current_directory(self, directory):
        self._populate_from_directory(directory)

    def get_ingest_files(self):
        return list(self._ingest_files)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._ingest_files)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(BatchPublisherModel.HEADER_LABELS)

    def headerData(self, section, orientation, role=None):
        if role is None:
            role = QtCore.Qt.DisplayRole

        if role != QtCore.Qt.DisplayRole:
            return None
        if orientation == QtCore.Qt.Horizontal:
            return BatchPublisherModel.HEADER_LABELS[section]

    def setData(self, index, value, role=None):
        column = index.column()
        row = index.row()
        ingest_file = self._ingest_files[row]
        if role == QtCore.Qt.EditRole:
            if column == BatchPublisherModel.COLUMN_OF_DIRECTORY:
                ingest_file.filepath = value
            elif column == BatchPublisherModel.COLUMN_OF_FOLDER:
                # Update product name
                ingest_file.folder_path = value
                # Update product name
                ingest_file.task_name = None
                # roles = [QtCore.Qt.UserRole]
                # self.dataChanged.emit(
                #     self.index(row, column),
                #     self.index(row, BatchPublisherModel.COLUMN_OF_TASK),
                #     roles)
            elif column == BatchPublisherModel.COLUMN_OF_TASK:
                ingest_file.task_name = value
                # # Update product name
                # self._controller._cache_task_names(ingest_file)
            elif column == BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE:
                ingest_file.product_type = value
                # # Update product name
                # self._controller._cache_task_names(ingest_file)
            elif column == BatchPublisherModel.COLUMN_OF_PRODUCT_NAME:
                ingest_file.product_name = value
            elif column == BatchPublisherModel.COLUMN_OF_REPRESENTATION:
                ingest_file.representation_name = value
            elif column == BatchPublisherModel.COLUMN_OF_VERSION:
                try:
                    ingest_file.version = int(value)
                except Exception:
                    ingest_file.version = None
            return True
        elif role == QtCore.Qt.CheckStateRole:
            if column == BatchPublisherModel.COLUMN_OF_CHECKBOX:
                enabled = True if value == QtCore.Qt.Checked else False
                ingest_file.enabled = enabled
                roles = [QtCore.Qt.ForegroundRole]
                self.dataChanged.emit(
                    self.index(row, column),
                    self.index(row, BatchPublisherModel.COLUMN_OF_VERSION),
                    roles)
                return True

    def data(self, index, role=QtCore.Qt.DisplayRole):
        column = index.column()
        row = index.row()
        ingest_file = self._ingest_files[row]
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            if column == BatchPublisherModel.COLUMN_OF_DIRECTORY:
                return ingest_file.filepath
            elif column == BatchPublisherModel.COLUMN_OF_FOLDER:
                return ingest_file.folder_path
            elif column == BatchPublisherModel.COLUMN_OF_TASK:
                return ingest_file.task_name
            elif column == BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE:
                return ingest_file.product_type
            elif column == BatchPublisherModel.COLUMN_OF_PRODUCT_NAME:
                return ingest_file.product_name
            elif column == BatchPublisherModel.COLUMN_OF_REPRESENTATION:
                return ingest_file.representation_name
            elif column == BatchPublisherModel.COLUMN_OF_VERSION:
                return str(ingest_file.version or "")
            # elif column == 1:
            #     magnitude = self.input_magnitudes[row]
            #     return f"{magnitude:.2f}"
        # elif role == QtCore.Qt.EditRole:
        #     return True
        elif role == QtCore.Qt.ForegroundRole:
            if ingest_file.defined and ingest_file.enabled:
                return QtGui.QColor(240, 240, 240)
            else:
                return QtGui.QColor(120, 120, 120)
        # elif role == QtCore.Qt.BackgroundRole:
        #     return QtGui.QColor(QtCore.Qt.white)
        # elif role == QtCore.Qt.TextAlignmentRole:
        #     return QtCore.Qt.AlignRight
        elif role == QtCore.Qt.ToolTipRole:
            project_name = self._controller.get_selected_project()
            tooltip = f"""
Enabled: <b>{ingest_file.enabled}</b>
<br>Filepath: <b>{ingest_file.filepath}</b>
<br>Folder (Asset): <b>{ingest_file.folder_path}</b>
<br>Task: <b>{ingest_file.task_name}</b>
<br>Product Type (Family): <b>{ingest_file.product_type}</b>
<br>Product Name (Subset): <b>{ingest_file.product_name}</b>
<br>Representation: <b>{ingest_file.representation_name}</b>
<br>Version: <b>{ingest_file.version}</b>
<br>Project: <b>{project_name}</b>
<br>Defined: <b>{ingest_file.defined}</b>
<br>Task Names: <b>{ingest_file.task_names}</b>"""
            return tooltip

        elif role == QtCore.Qt.CheckStateRole:
            if column == BatchPublisherModel.COLUMN_OF_CHECKBOX:
                return QtCore.Qt.Checked if ingest_file.enabled \
                    else QtCore.Qt.Unchecked
        elif role == QtCore.Qt.FontRole:
            # if column in [
            #         BatchPublisherModel.COLUMN_OF_DIRECTORY,
            #         BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE,
            #         BatchPublisherModel.COLUMN_OF_PRODUCT_NAME]:
            font = QtGui.QFont()
            font.setPointSize(9)
            return font

    #    return None

    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if index.column() == BatchPublisherModel.COLUMN_OF_CHECKBOX:
            flags |= QtCore.Qt.ItemIsUserCheckable
        elif index.column() > BatchPublisherModel.COLUMN_OF_DIRECTORY:
            flags |= QtCore.Qt.ItemIsEditable
        return flags

    def _populate_from_directory(self, directory):
        self.beginResetModel()
        self._ingest_files = self._controller.get_ingest_files(
            directory
        )
        self.endResetModel()

    def _change_project(self, project_name):
        """Clear the existing picked folder names, since project changed"""
        for row in range(self.rowCount()):
            ingest_file = self._ingest_files[row]
            ingest_file.folder_path = str()
            roles = [QtCore.Qt.DisplayRole]
            self.dataChanged.emit(
                self.index(row, self.COLUMN_OF_CHECKBOX),
                self.index(row, self.COLUMN_OF_VERSION),
                roles)
