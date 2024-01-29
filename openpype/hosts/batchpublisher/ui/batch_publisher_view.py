import functools

from qtpy import QtWidgets, QtCore, QtGui

from .batch_publisher_model import BatchPublisherModel


class BatchPublisherTableView(QtWidgets.QTableView):

    def __init__(self, controller, parent=None):
        super(BatchPublisherTableView, self).__init__(parent)

        model = BatchPublisherModel(controller)
        self.setModel(model)

        # self.setEditTriggers(self.NoEditTriggers)
        self.setSelectionMode(self.ExtendedSelection)
        # self.setSelectionBehavior(self.SelectRows)

        self.setColumnWidth(model.COLUMN_OF_ENABLED, 22)
        self.setColumnWidth(model.COLUMN_OF_FILEPATH, 700)
        self.setColumnWidth(model.COLUMN_OF_FOLDER, 200)
        self.setColumnWidth(model.COLUMN_OF_TASK, 90)
        self.setColumnWidth(model.COLUMN_OF_PRODUCT_TYPE, 140)
        self.setColumnWidth(model.COLUMN_OF_PRODUCT_NAME, 275)
        self.setColumnWidth(model.COLUMN_OF_REPRESENTATION, 120)
        self.setColumnWidth(model.COLUMN_OF_VERSION, 70)
        self.setColumnWidth(model.COLUMN_OF_COMMENT, 120)

        self.setTextElideMode(QtCore.Qt.ElideNone)
        self.setWordWrap(False)

        header = self.horizontalHeader()
        header.setSectionResizeMode(
            BatchPublisherModel.COLUMN_OF_FILEPATH,
            header.Stretch)
        self.verticalHeader().hide()

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_menu)

        self._model = model
        self._controller = controller

    def set_current_directory(self, directory):
        self._model.set_current_directory(directory)

    def get_product_items(self):
        return self._model.get_product_items()

    def commitData(self, editor):
        super(BatchPublisherTableView, self).commitData(editor)
        current_index = self.currentIndex()
        model = self.currentIndex().model()

        # Apply edit role to every other row of selection
        value = model.data(current_index, QtCore.Qt.EditRole)
        for qmodelindex in self.selectedIndexes():
            # row = qmodelindex.row()
            # product_item = model.product_items[row]
            model.setData(qmodelindex, value, role=QtCore.Qt.EditRole)

        # When changing folder we need to propagate
        # the chosen task value to every other row
        if current_index.column() == BatchPublisherModel.COLUMN_OF_FOLDER:
            qmodelindex_task = model.index(
                current_index.row(),
                BatchPublisherModel.COLUMN_OF_TASK)
            value_task = model.data(
                qmodelindex_task,
                QtCore.Qt.DisplayRole)
            for qmodelindex in self.selectedIndexes():
                qmodelindex_task = model.index(
                    qmodelindex.row(),
                    BatchPublisherModel.COLUMN_OF_TASK)
                model.setData(
                    qmodelindex_task,
                    value_task,
                    QtCore.Qt.EditRole)

    def _open_menu(self, pos):
        index = self.indexAt(pos)
        if not index.isValid():
            return
        product_items = self._model.get_product_items()
        product_item = product_items[index.row()]
        enabled = not product_item.enabled

        menu = QtWidgets.QMenu()

        action_copy = QtWidgets.QAction()
        action_copy.setText("Copy selected text")
        action_copy.triggered.connect(
            functools.partial(self.__copy_selected_text, pos))
        menu.addAction(action_copy)

        action_paste = QtWidgets.QAction()
        action_paste.setText("Paste text into selected cells")
        action_paste.triggered.connect(
            functools.partial(self.__paste_selected_text, pos))
        menu.addAction(action_paste)

        action_toggle_enabled = QtWidgets.QAction()
        action_toggle_enabled.setText("Toggle enabled")
        action_toggle_enabled.triggered.connect(
            functools.partial(self.__toggle_selected_enabled, enabled))
        menu.addAction(action_toggle_enabled)

        menu.exec_(self.viewport().mapToGlobal(pos))

    def __toggle_selected_enabled(self, enabled):
        product_items = self._model.get_product_items()
        for _index in self.selectedIndexes():
            product_item = product_items[_index.row()]
            product_item.enabled = enabled
            roles = [QtCore.Qt.DisplayRole]
            self._model.dataChanged.emit(
                self._model.index(_index.row(), self._model.COLUMN_OF_ENABLED),
                self._model.index(_index.row(), self._model.COLUMN_OF_COMMENT),
                roles)

    def __copy_selected_text(self, pos):
        index = self.indexAt(pos)
        if not index.isValid():
            return
        value = self._model.data(index)
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(value, QtGui.QClipboard.Clipboard)

    def __paste_selected_text(self, pos):
        index = self.indexAt(pos)
        if not index.isValid():
            return
        value = QtWidgets.QApplication.clipboard().text()
        column = index.column()
        for index in self.selectedIndexes():
            if column == self._model.COLUMN_OF_FILEPATH:
                continue
            self._model.setData(index, value, QtCore.Qt.EditRole)