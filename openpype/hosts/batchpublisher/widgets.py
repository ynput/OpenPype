

import glob
import os

from openpype import style

from openpype.client.entities import get_projects
from openpype.client.entities import get_assets
from openpype.client.entities import get_asset_by_name
from openpype.hosts.batchpublisher import publish
from openpype.pipeline.create import subset_name

from qtpy import QtWidgets, QtCore, QtGui

MODEL = None


HEADER_LABELS = [
    str(),
    "Filepath",
    "Folder (Asset)",
    "Task",
    "Product Type (Family)",
    "Product Name (subset)",
    "Variant",
    "Representation",
    "Version"]
COLUMN_OF_CHECKBOX = 0
COLUMN_OF_DIRECTORY = 1
COLUMN_OF_FOLDER = 2
COLUMN_OF_TASK = 3
COLUMN_OF_PRODUCT_TYPE = 4
COLUMN_OF_PRODUCT_NAME = 5
COLUMN_OF_VARIANT = 6
COLUMN_OF_REPRESENTATION = 7
COLUMN_OF_VERSION = 8

FILE_MAPPINGS = [
    {
        "glob": "*/fbx/*.fbx",
        "is_sequence": False,
        "product_type": "model",
        "variant": ""
    }
]


class IngestFile(object):

    def __init__(
        self,
        filepath,
        product_type,
        product_name,
        representation_name,
        version,
        enabled=True,
        folder_path=None,
        task_name=None,
    ):
        self.enabled = enabled
        self.filepath = filepath
        self.product_type = product_type
        self.product_name = product_name
        self.representation_name = representation_name
        self.version = version
        self._folder_path = folder_path or ""
        self._task_name = task_name or ""

        self._task_names = list()

    @property
    def folder_path(self):
        return self._folder_path

    @folder.setter
    def folder_path(self, folder_path):
        self._folder_path = folder_path

    @property
    def task_name(self):
        return self._task_name

    @task.setter
    def task_name(self, task_name):
        self._task_name = task_name

    @property
    def task_names(self):
        return self._task_names

    @property
    def defined(self):
        return all([
            bool(self.filepath),
            bool(self._folder_path),
            bool(self._task_name),
            bool(self.product_type),
            bool(self.product_name),
            bool(self.representation_name)])

    def publish(self):
        if not self._enabled:
            print("Skipping publish, not enabled: " + self._filepath)
            return
        if not self.defined:
            print("Skipping publish, not defined properly: " + self._filepath)
            return
        msg = "\nPublishing (ingesting): " + self._filepath
        msg += "\nAs Folder (Asset): {}".format(self._folder)
        msg += "\nTask: {}".format(self._task)
        msg += "\nProduct Type (Family): {}".format(self._product_type)
        msg += "\nProduct Name (Subset): {}".format(self._product_name)
        msg += "\nVariant: {}".format(self._variant)
        msg += "\nRepresentation: {}".format(self._representation)
        msg += "\nVersion: {}".format(self._version)
        msg += "\nProject: {}".format(MODEL.project)
        print(msg)
        publish_data = dict()
        expected_representations = dict()
        expected_representations[self._representation] = self._filepath
        publish.publish_version(
            MODEL.project,
            self._folder,
            self._task,
            self._product_type,
            self._product_name,
            expected_representations,
            publish_data)
        # publish.publish_version(
        #     project_name,
        #     asset_name,
        #     task_name,
        #     family_name,
        #     subset_name,
        #     expected_representations,
        #     publish_data,

    def calculate_product_name(self):
        msg = "\nCalulating product name"
        msg += "\nFolder: {}".format(self._folder)
        msg += "\nTask: {}".format(self._task)
        msg += "\nProduct Type (Family): {}".format(self._product_type)
        msg += "\nVariant: {}".format(self._variant)
        print(msg)
        if not self._folder:
            print("No folder set")
            self._task = str()
            self._product_name = str()
            return
        # Cache the auto calulated product name now.
        # The user can edit this value there after
        self._product_name = product_name


class BatchPublisherModel(QtCore.QAbstractTableModel):

    def __init__(self, data=None):
        super(BatchPublisherModel, self).__init__()

        self._project = str()
        self._ingest_filepaths = list()

        # self.populate_from_directory(directory)

    @property
    def project(self):
        return self._project

    @project.setter
    def project(self, project):
        msg = "Project name changed to: {}".format(project)
        print(msg)
        self._project = project

    @property
    def ingest_filepaths(self):
        return self._ingest_filepaths

    def populate_from_directory(self, directory):
        self.beginResetModel()
        self._ingest_filepaths = list()
        for file_mapping in FILE_MAPPINGS:
            product_type = file_mapping["product_type"]
            glob_full_path = directory + "/" + file_mapping["glob"]
            files = glob.glob(glob_full_path, recursive=False)
            for filepath in files:
                basename, ext = os.path.splitext(filename)
                ingest_filepath = IngestFile(
                    filepath,
                    product_type,
                    basename,
                    ext.lstrip(".")
                )
                self._ingest_filepaths.append(ingest_filepath)
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._ingest_filepaths)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(HEADER_LABELS)

    def headerData(self, section, orientation, role):
        if role != QtCore.Qt.DisplayRole:
            return None
        if orientation == QtCore.Qt.Horizontal:
            return HEADER_LABELS[section]

    def setData(self, index, value, role=None):
        column = index.column()
        row = index.row()
        ingest_filepath = self._ingest_filepaths[row]
        if role == QtCore.Qt.EditRole:
            if column == COLUMN_OF_DIRECTORY:
                ingest_filepath.filepath = value
            elif column == COLUMN_OF_FOLDER:
                # Update product name
                ingest_filepath.folder = value
                # Update product name
                ingest_filepath.calculate_product_name()
                # roles = [QtCore.Qt.UserRole]
                # self.dataChanged.emit(
                #     self.index(row, column),
                #     self.index(row, COLUMN_OF_TASK),
                #     roles)
            elif column == COLUMN_OF_TASK:
                ingest_filepath.task = value
                # Update product name
                ingest_filepath.calculate_product_name()
            elif column == COLUMN_OF_PRODUCT_TYPE:
                ingest_filepath.product_type = value
                # Update product name
                ingest_filepath.calculate_product_name()
            elif column == COLUMN_OF_PRODUCT_NAME:
                ingest_filepath.product_name = value
            elif column == COLUMN_OF_VARIANT:
                ingest_filepath.variant = value
            elif column == COLUMN_OF_REPRESENTATION:
                ingest_filepath.representation = value
            elif column == COLUMN_OF_VERSION:
                try:
                    ingest_filepath.version = int(value)
                except Exception:
                    pass
            return True
        elif role == QtCore.Qt.CheckStateRole:
            if column == COLUMN_OF_CHECKBOX:
                enabled = True if value == QtCore.Qt.Checked else False
                ingest_filepath.enabled = enabled
                roles = [QtCore.Qt.ForegroundRole]
                self.dataChanged.emit(
                    self.index(row, column),
                    self.index(row, COLUMN_OF_VERSION),
                    roles)
                return True

    def data(self, index, role=QtCore.Qt.DisplayRole):
        column = index.column()
        row = index.row()
        ingest_filepath = self._ingest_filepaths[row]
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            if column == COLUMN_OF_DIRECTORY:
                return ingest_filepath.filepath
            elif column == COLUMN_OF_FOLDER:
                return ingest_filepath.folder
            elif column == COLUMN_OF_TASK:
                return ingest_filepath.task
            elif column == COLUMN_OF_PRODUCT_TYPE:
                return ingest_filepath.product_type
            elif column == COLUMN_OF_PRODUCT_NAME:
                return ingest_filepath.product_name
            elif column == COLUMN_OF_VARIANT:
                return ingest_filepath.variant
            elif column == COLUMN_OF_REPRESENTATION:
                return ingest_filepath.representation
            elif column == COLUMN_OF_VERSION:
                return ingest_filepath.version or str()
            # elif column == 1:
            #     magnitude = self.input_magnitudes[row]
            #     return f"{magnitude:.2f}"
        # elif role == QtCore.Qt.EditRole:
        #     return True
        elif role == QtCore.Qt.ForegroundRole:
            if ingest_filepath.defined and ingest_filepath.enabled:
                return QtGui.QColor(240, 240, 240)
            else:
                return QtGui.QColor(120, 120, 120)
        # elif role == QtCore.Qt.BackgroundRole:
        #     return QtGui.QColor(QtCore.Qt.white)
        # elif role == QtCore.Qt.TextAlignmentRole:
        #     return QtCore.Qt.AlignRight
        elif role == QtCore.Qt.ToolTipRole:
            tooltip = str()
            tooltip += "Enabled: <b>" + str(
                ingest_filepath.enabled) + "</b>"
            tooltip += "<br>Filepath: <b>" + str(
                ingest_filepath.filepath) + "</b>"
            tooltip += "<br>Folder (Asset): <b>" + str(
                ingest_filepath.folder) + "</b>"
            tooltip += "<br>Task: <b>" + str(
                ingest_filepath.task) + "</b>"
            tooltip += "<br>Product Type (Family): <b>" + str(
                ingest_filepath.product_type) + "</b>"
            tooltip += "<br>Product Name (Subset): <b>" + str(
                ingest_filepath.product_name) + "</b>"
            tooltip += "<br>Variant: <b>" + str(
                ingest_filepath.variant) + "</b>"
            tooltip += "<br>Representation: <b>" + str(
                ingest_filepath.representation) + "</b>"
            tooltip += "<br>Version: <b>" + str(
                ingest_filepath.version) + "</b>"
            tooltip += "<br>Project: <b>" + str(
                self.project) + "</b>"
            tooltip += "<br>Defined: <b>" + str(
                ingest_filepath.defined) + "</b>"
            tooltip += "<br>Task Names: <b>" + str(
                ingest_filepath.task_names) + "</b>"
            return tooltip

        elif role == QtCore.Qt.CheckStateRole:
            if column == COLUMN_OF_CHECKBOX:
                return QtCore.Qt.Checked if ingest_filepath.enabled \
                    else QtCore.Qt.Unchecked
        elif role == QtCore.Qt.FontRole:
            # if column in [
            #         COLUMN_OF_DIRECTORY,
            #         COLUMN_OF_PRODUCT_TYPE,
            #         COLUMN_OF_PRODUCT_NAME]:
            font = QtGui.QFont()
            font.setPointSize(9)
            return font

    #    return None

    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if index.column() == COLUMN_OF_CHECKBOX:
            flags |= QtCore.Qt.ItemIsUserCheckable
        elif index.column() > COLUMN_OF_DIRECTORY:
            flags |= QtCore.Qt.ItemIsEditable
        return flags

    def publish(self):
        print("Publishing enabled and defined products...")
        for row in range(self.rowCount()):
            ingest_filepath = self._ingest_filepaths[row]
            if ingest_filepath.enabled and ingest_filepath.defined:
                ingest_filepath.publish()


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


class BatchPublisherTableDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self):
        super(BatchPublisherTableDelegate, self).__init__()
        # self._folder_names = [
        #     "assets",
        #     "assets/myasset",
        #     "assets/myasset/mytest"]
        self._folder_names = list()
        assets = get_assets(MODEL.project)
        for asset in assets:
            asset_name = "/".join(asset["data"]["parents"])
            asset_name += "/" + asset["name"]
            self._folder_names.append(asset_name)

    def createEditor(self, parent, option, index):
        model = index.model()
        ingest_filepath = model.ingest_filepaths[index.row()]

        if index.column() == COLUMN_OF_FOLDER:
            # clear the folder
            model.setData(index, str(), QtCore.Qt.EditRole)
            # clear the task
            model.setData(
                model.index(index.row(), COLUMN_OF_TASK),
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
            for asset in self._folder_names:
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

        elif index.column() == COLUMN_OF_TASK:
            # editor = QtWidgets.QLineEdit(parent)
            # completer = QtWidgets.QCompleter(
            #     ingest_filepath.task_names,
            #     self)
            # completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            # editor.setCompleter(completer)
            editor = QtWidgets.QComboBox(parent)
            editor.addItems(ingest_filepath.task_names)
            return editor

        elif index.column() == COLUMN_OF_PRODUCT_TYPE:
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
        if index.column() == COLUMN_OF_FOLDER:
            editor.blockSignals(True)
            value = index.data(QtCore.Qt.DisplayRole)
            # self._apply_asset_path_to_combo_box(editor, value)
            # Lets return the QComboxBox back to unselected state
            editor.setRootModelIndex(QtCore.QModelIndex())
            editor.setCurrentIndex(-1)
            editor.blockSignals(False)
        elif index.column() == COLUMN_OF_TASK:
            editor.blockSignals(True)
            value = index.data(QtCore.Qt.DisplayRole)
            row = editor.findText(value)
            editor.setCurrentIndex(row)
            editor.blockSignals(False)
        elif index.column() == COLUMN_OF_PRODUCT_TYPE:
            editor.blockSignals(True)
            value = index.data(QtCore.Qt.DisplayRole)
            row = editor.findText(value)
            editor.setCurrentIndex(row)
            editor.blockSignals(False)

    def setModelData(self, editor, model, index):
        model = index.model()
        if index.column() == COLUMN_OF_FOLDER:
            value = editor.model().data(
                editor.view().currentIndex(),
                QtCore.Qt.UserRole)
            model.setData(index, value, QtCore.Qt.EditRole)
        elif index.column() == COLUMN_OF_TASK:
            value = editor.currentText()
            model.setData(index, value, QtCore.Qt.EditRole)
        elif index.column() == COLUMN_OF_PRODUCT_TYPE:
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


class BatchPublisherTableView(QtWidgets.QTableView):

    def __init__(self, parent=None):
        super(BatchPublisherTableView, self).__init__(parent)

        model = BatchPublisherModel()
        global MODEL
        MODEL = model
        self.setModel(model)

        # self.setEditTriggers(self.NoEditTriggers)
        self.setSelectionMode(self.ExtendedSelection)
        # self.setSelectionBehavior(self.SelectRows)

        self.setColumnWidth(COLUMN_OF_CHECKBOX, 22)
        self.setColumnWidth(COLUMN_OF_DIRECTORY, 700)
        self.setColumnWidth(COLUMN_OF_FOLDER, 200)
        self.setColumnWidth(COLUMN_OF_TASK, 90)
        self.setColumnWidth(COLUMN_OF_PRODUCT_TYPE, 160)
        self.setColumnWidth(COLUMN_OF_PRODUCT_NAME, 250)
        self.setColumnWidth(COLUMN_OF_VARIANT, 200)
        self.setColumnWidth(COLUMN_OF_REPRESENTATION, 120)
        self.setColumnWidth(COLUMN_OF_VERSION, 70)

        self.setTextElideMode(QtCore.Qt.ElideNone)
        self.setWordWrap(False)

        # header = self.horizontalHeader()
        # header.setSectionResizeMode(COLUMN_OF_DIRECTORY, header.Stretch)
        # self.verticalHeader().hide()

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
        if current_index.column() == COLUMN_OF_FOLDER:
            value_task = model.data(
                model.index(current_index.row(), COLUMN_OF_TASK),
                QtCore.Qt.DisplayRole)
            for qmodelindex in self.selectedIndexes():
                qmodelindex_task = model.index(
                    qmodelindex.row(),
                    COLUMN_OF_TASK)
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
        model.publish()


class BatchPublisherWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(BatchPublisherWindow, self).__init__(parent)

        self.setWindowTitle("AYON Batch Publisher")
        self.resize(1850, 900)

        main_widget = QtWidgets.QWidget(self)

        self.setCentralWidget(main_widget)

        # --- Top inputs (project, directory) ---
        top_inputs_widget = QtWidgets.QWidget(self)

        project_combobox = QtWidgets.QComboBox(top_inputs_widget)
        project_combobox.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed)

        dir_inputs_widget = QtWidgets.QWidget(top_inputs_widget)
        dir_input = QtWidgets.QLineEdit(dir_inputs_widget)
        dir_browse_btn = QtWidgets.QPushButton("Browse", dir_inputs_widget)

        dir_inputs_layout = QtWidgets.QHBoxLayout(dir_inputs_widget)
        dir_inputs_layout.setContentsMargins(0, 0, 0, 0)
        dir_inputs_layout.addWidget(dir_input, 1)
        dir_inputs_layout.addWidget(dir_browse_btn, 0)

        top_inputs_layout = QtWidgets.QFormLayout(top_inputs_widget)
        top_inputs_layout.setContentsMargins(0, 0, 0, 0)
        top_inputs_layout.addRow("Choose project", project_combobox)
        top_inputs_layout.addRow("Directory to ingest", dir_inputs_widget)

        # --- Main view ---
        table_view = BatchPublisherTableView(main_widget)

        # --- Footer ---
        footer_widget = QtWidgets.QWidget(main_widget)

        publish_btn = QtWidgets.QPushButton("Publish", footer_widget)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(publish_btn, 0)

        # --- Main layout ---
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        main_layout.addWidget(top_inputs_widget, 0)
        main_layout.addWidget(table_view, 1)
        main_layout.addWidget(footer_widget, 0)

        self.setStyleSheet(style.load_stylesheet())

        project_combobox.currentIndexChanged.connect(
            self._on_project_changed)
        dir_browse_btn.clicked.connect(self._on_browse_button_clicked)
        publish_btn.clicked.connect(self._on_publish_button_clicked)

        # TODO do not use query in __init__
        # - add QStandardItemModel that handles refresh, or implement refresh
        #   on the window
        projects = get_projects()
        for project_dict in projects:
            project_combobox.addItem(project_dict["name"])

        # TODO remove from __init__
        self._on_project_changed()

        editors_delegate = BatchPublisherTableDelegate()
        table_view.setItemDelegateForColumn(
            COLUMN_OF_FOLDER, editors_delegate
        )
        table_view.setItemDelegateForColumn(
            COLUMN_OF_TASK, editors_delegate
        )
        table_view.setItemDelegateForColumn(
            COLUMN_OF_PRODUCT_TYPE, editors_delegate
        )

        self._project_combobox = project_combobox
        self._table_view = table_view
        self._editors_delegate = editors_delegate
        self._pushbutton_publish = publish_btn

    def _on_project_changed(self):
        project = str(self._project_combobox.currentText())
        MODEL.project = project

    def _on_browse_button_clicked(self):
        directory = self._lineedit_directory.text()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            dir=directory)
        if not directory:
            return
        self._lineedit_directory.setText(directory)
        model = self._table_view.model()
        model.populate_from_directory(directory)

    def _on_publish_button_clicked(self):
        self._table_view.publish()
