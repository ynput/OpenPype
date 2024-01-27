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
        self._product_items = []

    def set_current_directory(self, directory):
        self._populate_from_directory(directory)

    def get_product_items(self):
        return list(self._product_items)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._product_items)

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
        product_item = self._product_items[row]
        if role == QtCore.Qt.EditRole:
            if column == BatchPublisherModel.COLUMN_OF_DIRECTORY:
                product_item.filepath = value
            elif column == BatchPublisherModel.COLUMN_OF_FOLDER:
                # Update product name
                product_item.folder_path = value
                # Update product name
                product_item.task_name = None
                task_names = self._controller.get_task_names(value)
                if not product_item.task_name and task_names:
                    product_item.task_name = task_names[0]
                # roles = [QtCore.Qt.UserRole]
                # self.dataChanged.emit(
                #     self.index(row, column),
                #     self.index(row, BatchPublisherModel.COLUMN_OF_TASK),
                #     roles)
            elif column == BatchPublisherModel.COLUMN_OF_TASK:
                product_item.task_name = value
                # # Update product name
                # self._controller._cache_task_names(product_item)
            elif column == BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE:
                product_item.product_type = value
                # # Update product name
                # self._controller._cache_task_names(product_item)
            elif column == BatchPublisherModel.COLUMN_OF_PRODUCT_NAME:
                product_item.product_name = value
            elif column == BatchPublisherModel.COLUMN_OF_REPRESENTATION:
                product_item.representation_name = value
            elif column == BatchPublisherModel.COLUMN_OF_VERSION:
                try:
                    product_item.version = int(value)
                except Exception:
                    product_item.version = None
            return True
        elif role == QtCore.Qt.CheckStateRole:
            if column == BatchPublisherModel.COLUMN_OF_CHECKBOX:
                enabled = True if value == QtCore.Qt.Checked else False
                product_item.enabled = enabled
                roles = [QtCore.Qt.ForegroundRole]
                self.dataChanged.emit(
                    self.index(row, column),
                    self.index(row, BatchPublisherModel.COLUMN_OF_VERSION),
                    roles)
                return True

    def data(self, index, role=QtCore.Qt.DisplayRole):
        column = index.column()
        row = index.row()
        product_item = self._product_items[row]
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            if column == BatchPublisherModel.COLUMN_OF_DIRECTORY:
                return product_item.filepath
            elif column == BatchPublisherModel.COLUMN_OF_FOLDER:
                return product_item.folder_path
            elif column == BatchPublisherModel.COLUMN_OF_TASK:
                return product_item.task_name
            elif column == BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE:
                return product_item.product_type
            elif column == BatchPublisherModel.COLUMN_OF_PRODUCT_NAME:
                return product_item.product_name
            elif column == BatchPublisherModel.COLUMN_OF_REPRESENTATION:
                return product_item.representation_name
            elif column == BatchPublisherModel.COLUMN_OF_VERSION:
                return str(product_item.version or "")
            # elif column == 1:
            #     magnitude = self.input_magnitudes[row]
            #     return f"{magnitude:.2f}"
        # elif role == QtCore.Qt.EditRole:
        #     return True
        elif role == QtCore.Qt.ForegroundRole:
            if product_item.defined and product_item.enabled:
                return QtGui.QColor(240, 240, 240)
            else:
                return QtGui.QColor(120, 120, 120)
        # elif role == QtCore.Qt.BackgroundRole:
        #     return QtGui.QColor(QtCore.Qt.white)
        # elif role == QtCore.Qt.TextAlignmentRole:
        #     return QtCore.Qt.AlignRight
        elif role == QtCore.Qt.ToolTipRole:
            project_name = self._controller.get_selected_project_name()
            tooltip = f"""
Enabled: <b>{product_item.enabled}</b>
<br>Filepath: <b>{product_item.filepath}</b>
<br>Folder (Asset): <b>{product_item.folder_path}</b>
<br>Task: <b>{product_item.task_name}</b>
<br>Product Type (Family): <b>{product_item.product_type}</b>
<br>Product Name (Subset): <b>{product_item.product_name}</b>
<br>Representation: <b>{product_item.representation_name}</b>
<br>Version: <b>{product_item.version}</b>
<br>Project: <b>{project_name}</b>
<br>Defined: <b>{product_item.defined}</b>
<br>Task Names: <b>{product_item.task_names}</b>"""
            return tooltip

        elif role == QtCore.Qt.CheckStateRole:
            if column == BatchPublisherModel.COLUMN_OF_CHECKBOX:
                return QtCore.Qt.Checked if product_item.enabled \
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
        self._product_items = self._controller.get_product_items(
            directory
        )
        self.endResetModel()

    def _change_project(self, project_name):
        """Clear the existing picked folder names, since project changed"""
        for row in range(self.rowCount()):
            product_item = self._product_items[row]
            product_item.folder_path = None
            product_item.task_name = None
            roles = [QtCore.Qt.DisplayRole]
            self.dataChanged.emit(
                self.index(row, self.COLUMN_OF_CHECKBOX),
                self.index(row, self.COLUMN_OF_VERSION),
                roles)
