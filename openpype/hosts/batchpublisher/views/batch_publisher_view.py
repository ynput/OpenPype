


from openpype.hosts.batchpublisher.models.batch_publisher_model import \
    BatchPublisherModel

from qtpy import QtWidgets, QtCore


class BatchPublisherTableView(QtWidgets.QTableView):

    def __init__(self, controller, parent=None):
        super(BatchPublisherTableView, self).__init__(parent)

        self.controller = controller

        self.setModel(self.controller.model)

        # self.setEditTriggers(self.NoEditTriggers)
        self.setSelectionMode(self.ExtendedSelection)
        # self.setSelectionBehavior(self.SelectRows)

        self.setColumnWidth(BatchPublisherModel.COLUMN_OF_CHECKBOX, 22)
        self.setColumnWidth(BatchPublisherModel.COLUMN_OF_DIRECTORY, 700)
        self.setColumnWidth(BatchPublisherModel.COLUMN_OF_FOLDER, 200)
        self.setColumnWidth(BatchPublisherModel.COLUMN_OF_TASK, 90)
        self.setColumnWidth(BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE, 160)
        self.setColumnWidth(BatchPublisherModel.COLUMN_OF_PRODUCT_NAME, 250)
        self.setColumnWidth(BatchPublisherModel.COLUMN_OF_REPRESENTATION, 120)
        self.setColumnWidth(BatchPublisherModel.COLUMN_OF_VERSION, 70)

        self.setTextElideMode(QtCore.Qt.ElideNone)
        self.setWordWrap(False)

        header = self.horizontalHeader()
        header.setSectionResizeMode(BatchPublisherModel.COLUMN_OF_DIRECTORY, header.Stretch)
        self.verticalHeader().hide()

    def commitData(self, editor):
        super(BatchPublisherTableView, self).commitData(editor)
        current_index = self.currentIndex()
        model = self.currentIndex().model()

        # Apply edit role to every other row of selection
        value = model.data(current_index, QtCore.Qt.EditRole)
        for qmodelindex in self.selectedIndexes():
            # row = qmodelindex.row()
            # ingest_filepath = model.ingest_filepaths[row]
            model.setData(qmodelindex, value, role=QtCore.Qt.EditRole)

        # When changing folder we need to propagate
        # the chosen task value to every other row
        if current_index.column() == BatchPublisherModel.COLUMN_OF_FOLDER:
            value_task = model.data(
                model.index(current_index.row(), BatchPublisherModel.COLUMN_OF_TASK),
                QtCore.Qt.DisplayRole)
            for qmodelindex in self.selectedIndexes():
                qmodelindex_task = model.index(
                    qmodelindex.row(),
                    BatchPublisherModel.COLUMN_OF_TASK)
                model.setData(
                    qmodelindex_task,
                    value_task,
                    QtCore.Qt.EditRole)

    def publish(self):
        model = self.model()
        publish_count = 0
        enabled_count = 0
        defined_count = 0
        for row in range(model.rowCount()):
            ingest_filepath = model.ingest_filepaths[row]
            if ingest_filepath.enabled and ingest_filepath.defined:
                publish_count += 1
            if ingest_filepath.enabled:
                enabled_count += 1
            if ingest_filepath.defined:
                defined_count += 1
        if publish_count == 0:
            msg = "You must provide asset, task, family, "
            msg += "subset etc and they must be enabled"
            QtWidgets.QMessageBox.warning(
                None,
                "No enabled and defined ingest items!",
                msg)
            return
        elif publish_count > 0:
            msg = "Are you sure you want to publish "
            msg += "{} products".format(publish_count)
            result = QtWidgets.QMessageBox.question(
                None,
                "Okay to publish?",
                msg,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if result == QtWidgets.QMessageBox.No:
                print("User cancelled publishing")
                return
        elif enabled_count == 0:
            QtWidgets.QMessageBox.warning(
                None,
                "Nothing enabled for publish!",
                "There is no items enabled for publish")
            return
        elif defined_count == 0:
            QtWidgets.QMessageBox.warning(
                None,
                "No defined ingest items!",
                "You must provide asset, task, family, subset etc")
            return
        self.controller.publish()