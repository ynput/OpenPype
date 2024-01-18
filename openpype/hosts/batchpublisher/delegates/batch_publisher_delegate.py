

from openpype.hosts.batchpublisher.models.batch_publisher_model import \
    BatchPublisherModel

from qtpy import QtWidgets, QtCore, QtGui


class BatchPublisherTableDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, controller, parent=None):
        super(BatchPublisherTableDelegate, self).__init__(parent)
        self.controller = controller

    def createEditor(self, parent, option, index):
        model = index.model()
        ingest_filepath = model.ingest_filepaths[index.row()]

        if index.column() == BatchPublisherModel.COLUMN_OF_FOLDER:
            # clear the folder
            model.setData(index, str(), QtCore.Qt.EditRole)
            # clear the task
            model.setData(
                model.index(index.row(), BatchPublisherModel.COLUMN_OF_TASK),
                str(),
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
            assets_map = dict()
            for asset in self.controller.folder_names:
                asset_split = asset.split("/")
                self._populate_assets(
                    asset_split,
                    assets_map,
                    model,
                    depth=asset_split.count("/"))
            editor.view().expandAll()
            # editor.showPopup()
            # editor = QtWidgets.QLineEdit(parent)
            # completer = QtWidgets.QCompleter(self._folder_names, self)
            # completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            # editor.setCompleter(completer)
            return editor

        elif index.column() == BatchPublisherModel.COLUMN_OF_TASK:
            # editor = QtWidgets.QLineEdit(parent)
            # completer = QtWidgets.QCompleter(
            #     ingest_filepath.task_names,
            #     self)
            # completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            # editor.setCompleter(completer)
            editor = QtWidgets.QComboBox(parent)
            editor.addItems(ingest_filepath.task_names)
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
                QtCore.Qt.UserRole)
            model.setData(index, value, QtCore.Qt.EditRole)
        elif index.column() == BatchPublisherModel.COLUMN_OF_TASK:
            value = editor.currentText()
            model.setData(index, value, QtCore.Qt.EditRole)
        elif index.column() == BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE:
            value = editor.currentText()
            model.setData(index, value, QtCore.Qt.EditRole)

    def _populate_assets(self, asset_split, assets_map, model, depth=0):
        # where asset_split is for example ["assets", "myasset"]
        try:
            # asset_part at depth 1 is "myasset"
            asset_part = asset_split[depth]
        except Exception:
            return
        if not asset_part:
            return
        # path to current asset path being populated
        asset_path_so_far = "/".join(asset_split[0:depth + 1])
        # path to previous asset path being populated
        asset_path_previous = "/".join(asset_split[0:depth])
        # Check if a QStandardItem has already been generated for this part
        qstandarditem = assets_map.get(asset_path_so_far)
        # Get the last QStandardItem that is the parent for this level
        qstandarditem_previous = assets_map.get(asset_path_previous)
        if not qstandarditem:
            qstandarditem = QtGui.QStandardItem(asset_part)
            qstandarditem.setFlags(
                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            qstandarditem.setData(asset_path_so_far, QtCore.Qt.UserRole)
            qstandarditem.setData(depth, QtCore.Qt.UserRole + 1)
            qstandarditem.setData(
                asset_path_so_far + "<br>Depth: " + str(depth),
                QtCore.Qt.ToolTipRole)
            # Add top level standard item to model
            if depth == 0:
                model.appendRow(qstandarditem)
                assets_map[asset_path_so_far] = qstandarditem
            # Add child standard item based on previous standard item
            elif qstandarditem_previous:
                qstandarditem_previous.setFlags(QtCore.Qt.ItemIsEnabled)
                qstandarditem_previous.appendRow(qstandarditem)
                assets_map[asset_path_so_far] = qstandarditem
        self._populate_assets(asset_split, assets_map, model, depth=depth + 1)

    # def _apply_asset_path_to_combo_box(
    #         self,
    #         editor,
    #         asset_path,
    #         parent=QtCore.QModelIndex()):
    #     model = editor.model()
    #     found_qmodelindex = None
    #     for row in range(model.rowCount(parent)):
    #         qmodelindex = model.index(row, 0, parent);
    #         _asset_path = model.data(qmodelindex, QtCore.Qt.UserRole)
    #         if asset_path == _asset_path:
    #             editor.view().scrollTo(qmodelindex)
    #             editor.setRootModelIndex(qmodelindex.parent())
    #             editor.setCurrentIndex(qmodelindex.row())
    #             return qmodelindex
    #         if model.hasChildren(qmodelindex):
    #             found_qmodelindex = self._apply_asset_path_to_combo_box(
    #                 editor,
    #                 asset_path,
    #                 qmodelindex)
    #             if found_qmodelindex:
    #                 return found_qmodelindex
    #     return found_qmodelindex


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
