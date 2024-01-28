from qtpy import QtWidgets, QtCore

from .batch_publisher_model import BatchPublisherModel


class BatchPublisherTableView(QtWidgets.QTableView):

    def __init__(self, controller, parent=None):
        super(BatchPublisherTableView, self).__init__(parent)

        model = BatchPublisherModel(controller)
        self.setModel(model)

        # self.setEditTriggers(self.NoEditTriggers)
        self.setSelectionMode(self.ExtendedSelection)
        # self.setSelectionBehavior(self.SelectRows)

        self.setColumnWidth(model.COLUMN_OF_CHECKBOX, 22)
        self.setColumnWidth(model.COLUMN_OF_DIRECTORY, 700)
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
            BatchPublisherModel.COLUMN_OF_DIRECTORY,
            header.Stretch)
        self.verticalHeader().hide()

        self._model = model

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
