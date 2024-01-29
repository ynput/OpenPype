import collections

from qtpy import QtWidgets, QtCore, QtGui

from .batch_publisher_model import BatchPublisherModel

FOLDER_PATH_ROLE = QtCore.Qt.UserRole + 1


class BatchPublisherTableDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, controller, parent=None):
        super(BatchPublisherTableDelegate, self).__init__(parent)
        self._controller = controller

    def createEditor(self, parent, option, index):
        model = index.model()
        ingest_file = model.get_product_items()[index.row()]

        if index.column() == BatchPublisherModel.COLUMN_OF_FOLDER:
            # clear the folder
            model.setData(index, None, QtCore.Qt.EditRole)
            # clear the task
            model.setData(
                model.index(index.row(), BatchPublisherModel.COLUMN_OF_TASK),
                None,
                QtCore.Qt.EditRole)
            treeview = QtWidgets.QTreeView()
            treeview.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)
            treeview.setSelectionBehavior(QtWidgets.QTreeView.SelectRows)
            treeview.setSelectionMode(QtWidgets.QTreeView.SingleSelection)
            treeview.setItemsExpandable(True)
            treeview.header().setVisible(False)
            treeview.setMinimumHeight(250)
            editor = ComboBox(parent)
            editor.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
            editor.setView(treeview)
            model = QtGui.QStandardItemModel()
            editor.setModel(model)
            self._fill_model_with_hierarchy(model)
            editor.view().expandAll()
            # editor.showPopup()
            # editor = QtWidgets.QLineEdit(parent)
            # completer = QtWidgets.QCompleter(self._folder_names, self)
            # completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            # editor.setCompleter(completer)
            return editor

        elif index.column() == BatchPublisherModel.COLUMN_OF_TASK:
            task_names = self._controller.get_task_names(
                ingest_file.folder_path)
            # editor = QtWidgets.QLineEdit(parent)
            # completer = QtWidgets.QCompleter(
            #     task_names,
            #     self)
            # completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            # editor.setCompleter(completer)
            editor = QtWidgets.QComboBox(parent)
            editor.addItems(task_names)
            return editor

        elif index.column() == BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE:
            from openpype.plugins.publish import integrate
            product_types = sorted(integrate.IntegrateAsset.families)
            editor = QtWidgets.QComboBox(parent)
            editor.addItems(product_types)
            return editor
        # return QtWidgets.QStyledItemDelegate.createEditor(
        #     self,
        #     parent,
        #     option,
        #     index)

    def setEditorData(self, editor, index):
        if index.column() == BatchPublisherModel.COLUMN_OF_FOLDER:
            editor.blockSignals(True)
            value = index.data(QtCore.Qt.DisplayRole)
            # self._apply_asset_path_to_combo_box(editor, value)
            # Lets return the QComboxBox back to unselected state
            editor.setRootModelIndex(QtCore.QModelIndex())
            editor.setCurrentIndex(-1)
            editor.blockSignals(False)
        elif index.column() == BatchPublisherModel.COLUMN_OF_TASK:
            editor.blockSignals(True)
            value = index.data(QtCore.Qt.DisplayRole)
            row = editor.findText(value)
            editor.setCurrentIndex(row)
            editor.blockSignals(False)
        elif index.column() == BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE:
            editor.blockSignals(True)
            value = index.data(QtCore.Qt.DisplayRole)
            row = editor.findText(value)
            editor.setCurrentIndex(row)
            editor.blockSignals(False)

    def setModelData(self, editor, model, index):
        model = index.model()
        if index.column() == BatchPublisherModel.COLUMN_OF_FOLDER:
            value = editor.model().data(
                editor.view().currentIndex(),
                FOLDER_PATH_ROLE)
            model.setData(index, value, QtCore.Qt.EditRole)
        elif index.column() == BatchPublisherModel.COLUMN_OF_TASK:
            value = editor.currentText()
            model.setData(index, value, QtCore.Qt.EditRole)
        elif index.column() == BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE:
            value = editor.currentText()
            model.setData(index, value, QtCore.Qt.EditRole)

    def _fill_model_with_hierarchy(self, model):
        hierarchy_items = self._controller.get_hierarchy_items()
        hierarchy_items_by_parent_id = collections.defaultdict(list)
        for hierarchy_item in hierarchy_items:
            hierarchy_items_by_parent_id[hierarchy_item.parent_id].append(
                hierarchy_item
            )

        root_item = model.invisibleRootItem()

        hierarchy_queue = collections.deque()
        hierarchy_queue.append((root_item, None))

        while hierarchy_queue:
            (parent_item, parent_id) = hierarchy_queue.popleft()
            new_rows = []
            for hierarchy_item in hierarchy_items_by_parent_id[parent_id]:
                new_row = QtGui.QStandardItem(hierarchy_item.folder_name)
                new_row.setData(hierarchy_item.folder_path, FOLDER_PATH_ROLE)
                new_row.setData(
                    hierarchy_item.folder_path, QtCore.Qt.ToolTipRole)
                # new_row.setFlags(
                #     QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                new_rows.append(new_row)
                hierarchy_queue.append((new_row, hierarchy_item.folder_id))

            if new_rows:
                parent_item.appendRows(new_rows)


class ComboBox(QtWidgets.QComboBox):

    def keyPressEvent(self, event):
        # This is to prevent pressing "a" button with folder cell
        # selected and the "assets" is selected in QComboBox.
        # A default behaviour coming from QComboBox, when key is pressed
        # it selects first matching item in QComboBox root model index.
        # We don't want to select the "assets", since its not a full path
        # of folder.
        if event.type() == QtCore.QEvent.KeyPress:
            return
