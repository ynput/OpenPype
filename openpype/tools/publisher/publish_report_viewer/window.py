import os
import json
import six
import uuid

import appdirs
from qtpy import QtWidgets, QtCore, QtGui

from openpype import style
from openpype.resources import get_openpype_icon_filepath
from openpype.tools import resources
from openpype.tools.utils import (
    IconButton,
    paint_image_with_color
)

from openpype.tools.utils.delegates import PrettyTimeDelegate

if __package__:
    from .widgets import PublishReportViewerWidget
    from .report_items import PublishReport
else:
    from widgets import PublishReportViewerWidget
    from report_items import PublishReport


ITEM_ID_ROLE = QtCore.Qt.UserRole + 1


def get_reports_dir():
    """Root directory where publish reports are stored for next session.

    Returns:
        str: Path to directory where reports are stored.
    """

    report_dir = os.path.join(
        appdirs.user_data_dir("openpype", "pypeclub"),
        "publish_report_viewer"
    )
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
    return report_dir


class PublishReportItem:
    """Report item representing one file in report directory."""

    def __init__(self, content):
        item_id = content.get("id")
        changed = False
        if not item_id:
            item_id = str(uuid.uuid4())
            changed = True
            content["id"] = item_id

        if not content.get("report_version"):
            changed = True
            content["report_version"] = "0.0.1"

        report_path = os.path.join(get_reports_dir(), item_id)
        file_modified = None
        if os.path.exists(report_path):
            file_modified = os.path.getmtime(report_path)
        self.content = content
        self.report_path = report_path
        self.file_modified = file_modified
        self._loaded_label = content.get("label")
        self._changed = changed
        self.publish_report = PublishReport(content)

    @property
    def version(self):
        return self.content["report_version"]

    @property
    def id(self):
        return self.content["id"]

    def get_label(self):
        return self.content.get("label") or "Unfilled label"

    def set_label(self, label):
        if not label:
            self.content.pop("label", None)
        self.content["label"] = label

    label = property(get_label, set_label)

    def save(self):
        save = False
        if (
            self._changed
            or self._loaded_label != self.label
            or not os.path.exists(self.report_path)
            or self.file_modified != os.path.getmtime(self.report_path)
        ):
            save = True

        if not save:
            return

        with open(self.report_path, "w") as stream:
            json.dump(self.content, stream)

        self._loaded_label = self.content.get("label")
        self._changed = False
        self.file_modified = os.path.getmtime(self.report_path)

    @classmethod
    def from_filepath(cls, filepath):
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r") as stream:
                content = json.load(stream)

            return cls(content)
        except Exception:
            return None

    def remove_file(self):
        if os.path.exists(self.report_path):
            os.remove(self.report_path)

    def update_file_content(self):
        if not os.path.exists(self.report_path):
            return

        file_modified = os.path.getmtime(self.report_path)
        if file_modified == self.file_modified:
            return

        with open(self.report_path, "r") as stream:
            content = json.load(self.content, stream)

        item_id = content.get("id")
        version = content.get("report_version")
        if not item_id:
            item_id = str(uuid.uuid4())
            content["id"] = item_id

        if not version:
            version = "0.0.1"
            content["report_version"] = version

        self.content = content
        self.file_modified = file_modified


class PublisherReportHandler:
    """Class handling storing publish report tool."""

    def __init__(self):
        self._reports = None
        self._reports_by_id = {}

    def reset(self):
        self._reports = None
        self._reports_by_id = {}

    def list_reports(self):
        if self._reports is not None:
            return self._reports

        reports = []
        reports_by_id = {}
        report_dir = get_reports_dir()
        for filename in os.listdir(report_dir):
            ext = os.path.splitext(filename)[-1]
            if ext == ".json":
                continue
            filepath = os.path.join(report_dir, filename)
            item = PublishReportItem.from_filepath(filepath)
            reports.append(item)
            reports_by_id[item.id] = item

        self._reports = reports
        self._reports_by_id = reports_by_id
        return reports

    def remove_report_items(self, item_id):
        item = self._reports_by_id.get(item_id)
        if item:
            try:
                item.remove_file()
                self._reports_by_id.get(item_id)
            except Exception:
                pass


class LoadedFilesModel(QtGui.QStandardItemModel):
    def __init__(self, *args, **kwargs):
        super(LoadedFilesModel, self).__init__(*args, **kwargs)

        self._items_by_id = {}
        self._report_items_by_id = {}

        self._handler = PublisherReportHandler()

        self._loading_registry = False

    def refresh(self):
        self._handler.reset()
        self._items_by_id = {}
        self._report_items_by_id = {}

        new_items = []
        for report_item in self._handler.list_reports():
            item = self._create_item(report_item)
            self._report_items_by_id[report_item.id] = report_item
            self._items_by_id[report_item.id] = item
            new_items.append(item)

        if new_items:
            root_item = self.invisibleRootItem()
            root_item.appendRows(new_items)

    def headerData(self, section, orientation, role):
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            if section == 0:
                return "Exports"
            if section == 1:
                return "Modified"
            return ""
        super(LoadedFilesModel, self).headerData(section, orientation, role)

    def data(self, index, role=None):
        if role is None:
            role = QtCore.Qt.DisplayRole

        col = index.column()
        if col != 0:
            index = self.index(index.row(), 0, index.parent())

        return super(LoadedFilesModel, self).data(index, role)

    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            item_id = index.data(ITEM_ID_ROLE)
            report_item = self._report_items_by_id.get(item_id)
            if report_item is not None:
                report_item.label = value
                report_item.save()
                value = report_item.label

        return super(LoadedFilesModel, self).setData(index, value, role)

    def _create_item(self, report_item):
        if report_item.id in self._items_by_id:
            return None

        item = QtGui.QStandardItem(report_item.label)
        item.setColumnCount(self.columnCount())
        item.setData(report_item.id, ITEM_ID_ROLE)

        return item

    def add_filepaths(self, filepaths):
        if not filepaths:
            return

        if isinstance(filepaths, six.string_types):
            filepaths = [filepaths]

        filtered_paths = []
        for filepath in filepaths:
            normalized_path = os.path.normpath(filepath)
            if (
                os.path.exists(normalized_path)
                and normalized_path not in filtered_paths
            ):
                filtered_paths.append(normalized_path)

        if not filtered_paths:
            return

        new_items = []
        for normalized_path in filtered_paths:
            try:
                with open(normalized_path, "r") as stream:
                    data = json.load(stream)
                report_item = PublishReportItem(data)
            except Exception:
                # TODO handle errors
                continue

            label = data.get("label")
            if not label:
                report_item.label = (
                    os.path.splitext(os.path.basename(filepath))[0]
                )

            item = self._create_item(report_item)
            if item is None:
                continue

            new_items.append(item)
            report_item.save()
            self._items_by_id[report_item.id] = item
            self._report_items_by_id[report_item.id] = report_item

        if new_items:
            root_item = self.invisibleRootItem()
            root_item.appendRows(new_items)

    def remove_item_by_id(self, item_id):
        report_item = self._report_items_by_id.get(item_id)
        if not report_item:
            return

        self._handler.remove_report_items(item_id)
        item = self._items_by_id.get(item_id)

        parent = self.invisibleRootItem()
        parent.removeRow(item.row())

    def get_report_by_id(self, item_id):
        report_item = self._report_items_by_id.get(item_id)
        if report_item:
            return report_item.publish_report
        return None


class LoadedFilesView(QtWidgets.QTreeView):
    selection_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(LoadedFilesView, self).__init__(*args, **kwargs)
        self.setEditTriggers(
            self.EditKeyPressed | self.SelectedClicked | self.DoubleClicked
        )
        self.setIndentation(0)
        self.setAlternatingRowColors(True)

        model = LoadedFilesModel()
        self.setModel(model)

        time_delegate = PrettyTimeDelegate()
        self.setItemDelegateForColumn(1, time_delegate)

        remove_btn = IconButton(self)
        remove_icon_path = resources.get_icon_path("delete")
        loaded_remove_image = QtGui.QImage(remove_icon_path)
        pix = paint_image_with_color(loaded_remove_image, QtCore.Qt.white)
        icon = QtGui.QIcon(pix)
        remove_btn.setIcon(icon)

        model.rowsInserted.connect(self._on_rows_inserted)
        remove_btn.clicked.connect(self._on_remove_clicked)
        self.selectionModel().selectionChanged.connect(
            self._on_selection_change
        )

        self._model = model
        self._time_delegate = time_delegate
        self._remove_btn = remove_btn

    def _update_remove_btn(self):
        viewport = self.viewport()
        height = viewport.height() + self.header().height()
        pos_x = viewport.width() - self._remove_btn.width() - 5
        pos_y = height - self._remove_btn.height() - 5
        self._remove_btn.move(max(0, pos_x), max(0, pos_y))

    def _on_rows_inserted(self):
        header = self.header()
        header.resizeSections(header.ResizeToContents)
        self._update_remove_btn()

    def resizeEvent(self, event):
        super(LoadedFilesView, self).resizeEvent(event)
        self._update_remove_btn()

    def showEvent(self, event):
        super(LoadedFilesView, self).showEvent(event)
        self._model.refresh()
        header = self.header()
        header.resizeSections(header.ResizeToContents)
        self._update_remove_btn()

    def _on_selection_change(self):
        self.selection_changed.emit()

    def add_filepaths(self, filepaths):
        self._model.add_filepaths(filepaths)
        self._fill_selection()

    def remove_item_by_id(self, item_id):
        self._model.remove_item_by_id(item_id)
        self._fill_selection()

    def _on_remove_clicked(self):
        index = self.currentIndex()
        item_id = index.data(ITEM_ID_ROLE)
        self.remove_item_by_id(item_id)

    def _fill_selection(self):
        index = self.currentIndex()
        if index.isValid():
            return

        index = self._model.index(0, 0)
        if index.isValid():
            self.setCurrentIndex(index)

    def get_current_report(self):
        index = self.currentIndex()
        item_id = index.data(ITEM_ID_ROLE)
        return self._model.get_report_by_id(item_id)


class LoadedFilesWidget(QtWidgets.QWidget):
    report_changed = QtCore.Signal()

    def __init__(self, parent):
        super(LoadedFilesWidget, self).__init__(parent)

        self.setAcceptDrops(True)

        view = LoadedFilesView(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(view, 1)

        view.selection_changed.connect(self._on_report_change)

        self._view = view

    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()

    def dragLeaveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            filepaths = []
            for url in mime_data.urls():
                filepath = url.toLocalFile()
                ext = os.path.splitext(filepath)[-1]
                if os.path.exists(filepath) and ext == ".json":
                    filepaths.append(filepath)
            self._add_filepaths(filepaths)
        event.accept()

    def _on_report_change(self):
        self.report_changed.emit()

    def _add_filepaths(self, filepaths):
        self._view.add_filepaths(filepaths)

    def get_current_report(self):
        return self._view.get_current_report()


class PublishReportViewerWindow(QtWidgets.QWidget):
    default_width = 1200
    default_height = 600

    def __init__(self, parent=None):
        super(PublishReportViewerWindow, self).__init__(parent)
        self.setWindowTitle("Publish report viewer")
        icon = QtGui.QIcon(get_openpype_icon_filepath())
        self.setWindowIcon(icon)

        body = QtWidgets.QSplitter(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        body.setOrientation(QtCore.Qt.Horizontal)

        loaded_files_widget = LoadedFilesWidget(body)
        main_widget = PublishReportViewerWidget(body)

        body.addWidget(loaded_files_widget)
        body.addWidget(main_widget)
        body.setStretchFactor(0, 70)
        body.setStretchFactor(1, 65)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(body, 1)

        loaded_files_widget.report_changed.connect(self._on_report_change)

        self._loaded_files_widget = loaded_files_widget
        self._main_widget = main_widget

        self.resize(self.default_width, self.default_height)
        self.setStyleSheet(style.load_stylesheet())

    def _on_report_change(self):
        report = self._loaded_files_widget.get_current_report()
        self.set_report(report)

    def set_report(self, report_data):
        self._main_widget.set_report(report_data)
