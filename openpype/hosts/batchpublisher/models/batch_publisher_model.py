

import glob
import os

from openpype.client.entities import (
    get_asset_by_name,
    get_assets)
from openpype.hosts.batchpublisher import publish

from qtpy import QtCore, QtGui

# TODO: add to OpenPype settings so other studios can change
FILE_MAPPINGS = [
    {
        "glob": "*/fbx/*.fbx",
        "is_sequence": False,
        "product_type": "model",
    }
]


class IngestFile(object):

    def __init__(
            self,
            ingest_settings,
            filepath,
            product_type,
            product_name,
            representation_name,
            version=None,
            enabled=True,
            folder_path=None,
            task_name=None):
        self.ingest_settings = ingest_settings
        self.enabled = enabled
        self.filepath = filepath
        self.product_type = product_type
        self.product_name = product_name or ""
        self.representation_name = representation_name
        self.version = version
        self.folder_path = folder_path or ""
        self.task_name = task_name or ""
        self.task_names = []

    @property
    def defined(self):
        return all([
            bool(self.filepath),
            bool(self.folder_path),
            bool(self.task_name),
            bool(self.product_type),
            bool(self.product_name),
            bool(self.representation_name)])

    def publish(self):
        if not self.enabled:
            print("Skipping publish, not enabled: " + self.filepath)
            return
        if not self.defined:
            print("Skipping publish, not defined properly: " + self.filepath)
            return
        msg = f"""
Publishing (ingesting): {self.filepath}
As Folder (Asset): {self.folder_path}
Task: {self.task_name}
Product Type (Family): {self.product_type}
Product Name (Subset): {self.product_name}
Representation: {self.representation_name}
Version: {self.version}"
Project: {self.ingest_settings.project}"""
        print(msg)
        publish_data = dict()
        expected_representations = dict()
        expected_representations[self.representation_name] = self.filepath
        publish.publish_version(
            self.ingest_settings.project,
            self.folder_path,
            self.task_name,
            self.product_type,
            self.product_name,
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

    def _cache_task_names(self):
        if not self.folder_path:
            self.task_name = str()
            return
        asset_doc = get_asset_by_name(
            self.ingest_settings.project,
            self.folder_path)
        if not asset_doc:
            self.task_name = str()
            return
        # Since we have the tasks available for the asset (folder) cache it now
        self.task_names = list(asset_doc["data"]["tasks"].keys())
        # Default to the first task available
        if not self.task_name and self.task_names:
            self.task_name = self.task_names[0]


class IngestSettings(object):
    """
    Used to store ingest settings that are global
    """

    def __init__(self, project=""):
        self._project = ""
        self._folder_names = []

    @property
    def project(self):
        return self._project

    @project.setter
    def project(self, project):
        msg = "Project name changed to: {}".format(project)
        print(msg)
        self._project = project
        # Update cache of asset names for project
        # self._folder_names = [
        #     "assets",
        #     "assets/myasset",
        #     "assets/myasset/mytest"]
        self._folder_names = list()
        assets = get_assets(project)
        for asset in assets:
            asset_name = "/".join(asset["data"]["parents"])
            asset_name += "/" + asset["name"]
            self._folder_names.append(asset_name)

    @property
    def folder_names(self):
        return self._folder_names


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

    def __init__(self, data=None):
        super(BatchPublisherModel, self).__init__()

        self._ingest_filepaths = list()
        self.ingest_settings = IngestSettings()

        # self.populate_from_directory(directory)

    @property
    def project(self):
        return self.ingest_settings.project

    @project.setter
    def project(self, project):
        self.ingest_settings.project = project

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
                filename = os.path.basename(filepath)
                representation_name = os.path.splitext(
                    filename)[1].lstrip(".")
                product_name = os.path.splitext(filename)[0]
                ingest_filepath = IngestFile(
                    self.ingest_settings,
                    filepath,
                    product_type,
                    product_name,
                    representation_name)
                # IngestFile(
                #     filepath,
                #     product_type,
                #     representation_name,
                #     version=None,
                #     product_name=None,
                #     enabled=True,
                #     folder_path=None,
                #     task_name=None)
                self._ingest_filepaths.append(ingest_filepath)
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._ingest_filepaths)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(BatchPublisherModel.HEADER_LABELS)

    def headerData(self, section, orientation, role):
        if role != QtCore.Qt.DisplayRole:
            return None
        if orientation == QtCore.Qt.Horizontal:
            return BatchPublisherModel.HEADER_LABELS[section]

    def setData(self, index, value, role=None):
        column = index.column()
        row = index.row()
        ingest_filepath = self._ingest_filepaths[row]
        if role == QtCore.Qt.EditRole:
            if column == BatchPublisherModel.COLUMN_OF_DIRECTORY:
                ingest_filepath.filepath = value
            elif column == BatchPublisherModel.COLUMN_OF_FOLDER:
                # Update product name
                ingest_filepath.folder_path = value
                # Update product name
                ingest_filepath._cache_task_names()
                # roles = [QtCore.Qt.UserRole]
                # self.dataChanged.emit(
                #     self.index(row, column),
                #     self.index(row, BatchPublisherModel.COLUMN_OF_TASK),
                #     roles)
            elif column == BatchPublisherModel.COLUMN_OF_TASK:
                ingest_filepath.task_name = value
                # # Update product name
                # ingest_filepath._cache_task_names()
            elif column == BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE:
                ingest_filepath.product_type = value
                # # Update product name
                # ingest_filepath._cache_task_names()
            elif column == BatchPublisherModel.COLUMN_OF_PRODUCT_NAME:
                ingest_filepath.product_name = value
            elif column == BatchPublisherModel.COLUMN_OF_REPRESENTATION:
                ingest_filepath.representation_name = value
            elif column == BatchPublisherModel.COLUMN_OF_VERSION:
                try:
                    ingest_filepath.version = int(value)
                except Exception:
                    ingest_filepath.version = None
            return True
        elif role == QtCore.Qt.CheckStateRole:
            if column == BatchPublisherModel.COLUMN_OF_CHECKBOX:
                enabled = True if value == QtCore.Qt.Checked else False
                ingest_filepath.enabled = enabled
                roles = [QtCore.Qt.ForegroundRole]
                self.dataChanged.emit(
                    self.index(row, column),
                    self.index(row, BatchPublisherModel.COLUMN_OF_VERSION),
                    roles)
                return True

    def data(self, index, role=QtCore.Qt.DisplayRole):
        column = index.column()
        row = index.row()
        ingest_filepath = self._ingest_filepaths[row]
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            if column == BatchPublisherModel.COLUMN_OF_DIRECTORY:
                return ingest_filepath.filepath
            elif column == BatchPublisherModel.COLUMN_OF_FOLDER:
                return ingest_filepath.folder_path
            elif column == BatchPublisherModel.COLUMN_OF_TASK:
                return ingest_filepath.task_name
            elif column == BatchPublisherModel.COLUMN_OF_PRODUCT_TYPE:
                return ingest_filepath.product_type
            elif column == BatchPublisherModel.COLUMN_OF_PRODUCT_NAME:
                return ingest_filepath.product_name
            elif column == BatchPublisherModel.COLUMN_OF_REPRESENTATION:
                return ingest_filepath.representation_name
            elif column == BatchPublisherModel.COLUMN_OF_VERSION:
                return str(ingest_filepath.version or "")
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
            tooltip = f"""
Enabled: <b>{ingest_filepath.enabled}</b>
<br>Filepath: <b>{ingest_filepath.filepath}</b>
<br>Folder (Asset): <b>{ingest_filepath.folder_path}</b>
<br>Task: <b>{ingest_filepath.task_name}</b>
<br>Product Type (Family): <b>{ingest_filepath.product_type}</b>
<br>Product Name (Subset): <b>{ingest_filepath.product_name}</b>
<br>Representation: <b>{ingest_filepath.representation_name}</b>
<br>Version: <b>{ingest_filepath.version}</b>
<br>Project: <b>{self.project}</b>
<br>Defined: <b>{ingest_filepath.defined}</b>
<br>Task Names: <b>{ingest_filepath.task_names}</b>"""
            return tooltip

        elif role == QtCore.Qt.CheckStateRole:
            if column == BatchPublisherModel.COLUMN_OF_CHECKBOX:
                return QtCore.Qt.Checked if ingest_filepath.enabled \
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

    def publish(self):
        print("Publishing enabled and defined products...")
        for row in range(self.rowCount()):
            ingest_filepath = self._ingest_filepaths[row]
            if ingest_filepath.enabled and ingest_filepath.defined:
                ingest_filepath.publish()
