import os
import json
import six
import appdirs
from Qt import QtWidgets, QtCore, QtGui

from openpype import style
from openpype.lib import JSONSettingRegistry
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


FILEPATH_ROLE = QtCore.Qt.UserRole + 1
MODIFIED_ROLE = QtCore.Qt.UserRole + 2


class PublisherReportRegistry(JSONSettingRegistry):
    """Class handling storing publish report tool.

    Attributes:
        vendor (str): Name used for path construction.
        product (str): Additional name used for path construction.

    """

    def __init__(self):
        self.vendor = "pypeclub"
        self.product = "openpype"
        name = "publish_report_viewer"
        path = appdirs.user_data_dir(self.product, self.vendor)
        super(PublisherReportRegistry, self).__init__(name, path)


class LoadedFilesMopdel(QtGui.QStandardItemModel):
    def __init__(self, *args, **kwargs):
        super(LoadedFilesMopdel, self).__init__(*args, **kwargs)
        self.setColumnCount(2)
        self._items_by_filepath = {}
        self._reports_by_filepath = {}

        self._registry = PublisherReportRegistry()

        self._loading_registry = False
        self._load_registry()

    def headerData(self, section, orientation, role):
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            if section == 0:
                return "Exports"
            if section == 1:
                return "Modified"
            return ""
        super(LoadedFilesMopdel, self).headerData(section, orientation, role)

    def _load_registry(self):
        self._loading_registry = True
        try:
            filepaths = self._registry.get_item("filepaths")
            self.add_filepaths(filepaths)
        except ValueError:
            pass
        self._loading_registry = False

    def _store_registry(self):
        if self._loading_registry:
            return
        filepaths = list(self._items_by_filepath.keys())
        self._registry.set_item("filepaths", filepaths)

    def data(self, index, role=None):
        if role is None:
            role = QtCore.Qt.DisplayRole

        col = index.column()
        if col != 0:
            index = self.index(index.row(), 0, index.parent())

        if role == QtCore.Qt.ToolTipRole:
            if col == 0:
                role = FILEPATH_ROLE
            elif col == 1:
                return "File modified"
            return None

        elif role == QtCore.Qt.DisplayRole:
            if col == 1:
                role = MODIFIED_ROLE
        return super(LoadedFilesMopdel, self).data(index, role)

    def add_filepaths(self, filepaths):
        if not filepaths:
            return

        if isinstance(filepaths, six.string_types):
            filepaths = [filepaths]

        filtered_paths = []
        for filepath in filepaths:
            normalized_path = os.path.normpath(filepath)
            if normalized_path in self._items_by_filepath:
                continue

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
                report = PublishReport(data)
            except Exception:
                # TODO handle errors
                continue

            modified = os.path.getmtime(normalized_path)
            item = QtGui.QStandardItem(os.path.basename(normalized_path))
            item.setColumnCount(self.columnCount())
            item.setData(normalized_path, FILEPATH_ROLE)
            item.setData(modified, MODIFIED_ROLE)
            new_items.append(item)
            self._items_by_filepath[normalized_path] = item
            self._reports_by_filepath[normalized_path] = report

        if not new_items:
            return

        parent = self.invisibleRootItem()
        parent.appendRows(new_items)

        self._store_registry()

    def remove_filepaths(self, filepaths):
        if not filepaths:
            return

        if isinstance(filepaths, six.string_types):
            filepaths = [filepaths]

        filtered_paths = []
        for filepath in filepaths:
            normalized_path = os.path.normpath(filepath)
            if normalized_path in self._items_by_filepath:
                filtered_paths.append(normalized_path)

        if not filtered_paths:
            return

        parent = self.invisibleRootItem()
        for filepath in filtered_paths:
            self._reports_by_filepath.pop(normalized_path)
            item = self._items_by_filepath.pop(filepath)
            parent.removeRow(item.row())

        self._store_registry()

    def get_report_by_filepath(self, filepath):
        return self._reports_by_filepath.get(filepath)


class LoadedFilesView(QtWidgets.QTreeView):
    selection_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(LoadedFilesView, self).__init__(*args, **kwargs)
        self.setEditTriggers(self.NoEditTriggers)
        self.setIndentation(0)
        self.setAlternatingRowColors(True)

        model = LoadedFilesMopdel()
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

    def resizeEvent(self, event):
        super(LoadedFilesView, self).resizeEvent(event)
        self._update_remove_btn()

    def showEvent(self, event):
        super(LoadedFilesView, self).showEvent(event)
        self._update_remove_btn()
        header = self.header()
        header.resizeSections(header.ResizeToContents)

    def _on_selection_change(self):
        self.selection_changed.emit()

    def add_filepaths(self, filepaths):
        self._model.add_filepaths(filepaths)
        self._fill_selection()

    def remove_filepaths(self, filepaths):
        self._model.remove_filepaths(filepaths)
        self._fill_selection()

    def _on_remove_clicked(self):
        index = self.currentIndex()
        filepath = index.data(FILEPATH_ROLE)
        self.remove_filepaths(filepath)

    def _fill_selection(self):
        index = self.currentIndex()
        if index.isValid():
            return

        index = self._model.index(0, 0)
        if index.isValid():
            self.setCurrentIndex(index)

    def get_current_report(self):
        index = self.currentIndex()
        filepath = index.data(FILEPATH_ROLE)
        return self._model.get_report_by_filepath(filepath)


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
