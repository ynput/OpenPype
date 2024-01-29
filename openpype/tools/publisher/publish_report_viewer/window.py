import os
import json
import six
import uuid

import appdirs
import arrow
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
ITEM_CREATED_AT_ROLE = QtCore.Qt.UserRole + 2


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
        changed = self._fix_content(content)

        report_path = os.path.join(get_reports_dir(), content["id"])
        file_modified = None
        if os.path.exists(report_path):
            file_modified = os.path.getmtime(report_path)

        created_at_obj = arrow.get(content["created_at"]).to("local")
        created_at = created_at_obj.float_timestamp

        self.content = content
        self.report_path = report_path
        self.file_modified = file_modified
        self.created_at = float(created_at)
        self._loaded_label = content.get("label")
        self._changed = changed
        self.publish_report = PublishReport(content)

    @property
    def version(self):
        """Publish report version.

        Returns:
            str: Publish report version.
        """
        return self.content["report_version"]

    @property
    def id(self):
        """Publish report id.

        Returns:
            str: Publish report id.
        """

        return self.content["id"]

    def get_label(self):
        """Publish report label.

        Returns:
            str: Publish report label showed in UI.
        """

        return self.content.get("label") or "Unfilled label"

    def set_label(self, label):
        """Set publish report label.

        Args:
            label (str): New publish report label.
        """

        if not label:
            self.content.pop("label", None)
        self.content["label"] = label

    label = property(get_label, set_label)

    @property
    def loaded_label(self):
        return self._loaded_label

    def mark_as_changed(self):
        """Mark report as changed."""

        self._changed = True

    def save(self):
        """Save publish report to file."""

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
        """Create report item from file.

        Args:
            filepath (str): Path to report file. Content must be json.

        Returns:
            PublishReportItem: Report item.
        """

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r") as stream:
                content = json.load(stream)

            file_modified = os.path.getmtime(filepath)
            changed = cls._fix_content(content, file_modified=file_modified)
            obj = cls(content)
            if changed:
                obj.mark_as_changed()
            return obj

        except Exception:
            return None

    def remove_file(self):
        """Remove report file."""

        if os.path.exists(self.report_path):
            os.remove(self.report_path)

    def update_file_content(self):
        """Update report content in file."""

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

    @classmethod
    def _fix_content(cls, content, file_modified=None):
        """Fix content for backward compatibility of older report items.

        Args:
            content (dict[str, Any]): Report content.
            file_modified (Optional[float]): File modification time.

        Returns:
            bool: True if content was changed, False otherwise.
        """

        # Fix created_at key
        changed = cls._fix_created_at(content, file_modified)

        # NOTE backward compatibility for 'id' and 'report_version' is from
        #    28.10.2022 https://github.com/ynput/OpenPype/pull/4040
        # We can probably safely remove it

        # Fix missing 'id'
        item_id = content.get("id")
        if not item_id:
            item_id = str(uuid.uuid4())
            changed = True
            content["id"] = item_id

        # Fix missing 'report_version'
        if not content.get("report_version"):
            changed = True
            content["report_version"] = "0.0.1"
        return changed

    @classmethod
    def _fix_created_at(cls, content, file_modified):
        # Key 'create_at' was added in report version 1.0.1
        created_at = content.get("created_at")
        if created_at:
            return False

        # Auto fix 'created_at', use file modification time if it is not set
        #   or current time if modification could not be received.
        if file_modified is not None:
            created_at_obj = arrow.Arrow.fromtimestamp(file_modified)
        else:
            created_at_obj = arrow.utcnow()
        content["created_at"] = created_at_obj.to("local").isoformat()
        return True


class PublisherReportHandler:
    """Class handling storing publish report items."""

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
            if item is not None:
                reports.append(item)
                reports_by_id[item.id] = item

        self._reports = reports
        self._reports_by_id = reports_by_id
        return reports

    def remove_report_item(self, item_id):
        """Remove report item by id.

        Remove from cache and also remove the file with the content.

        Args:
            item_id (str): Report item id.
        """

        item = self._reports_by_id.get(item_id)
        if item:
            try:
                item.remove_file()
                self._reports_by_id.get(item_id)
            except Exception:
                pass


class LoadedFilesModel(QtGui.QStandardItemModel):
    header_labels = ("Reports", "Created")

    def __init__(self, *args, **kwargs):
        super(LoadedFilesModel, self).__init__(*args, **kwargs)

        # Column count must be set before setting header data
        self.setColumnCount(len(self.header_labels))
        for col, label in enumerate(self.header_labels):
            self.setHeaderData(col, QtCore.Qt.Horizontal, label)

        self._items_by_id = {}
        self._report_items_by_id = {}

        self._handler = PublisherReportHandler()

        self._loading_registry = False

    def refresh(self):
        root_item = self.invisibleRootItem()
        if root_item.rowCount() > 0:
            root_item.removeRows(0, root_item.rowCount())
        self._items_by_id = {}
        self._report_items_by_id = {}

        self._handler.reset()

        new_items = []
        for report_item in self._handler.list_reports():
            item = self._create_item(report_item)
            self._report_items_by_id[report_item.id] = report_item
            self._items_by_id[report_item.id] = item
            new_items.append(item)

        if new_items:
            root_item = self.invisibleRootItem()
            root_item.appendRows(new_items)

    def data(self, index, role=None):
        if role is None:
            role = QtCore.Qt.DisplayRole

        col = index.column()
        if col == 1:
            if role in (
                QtCore.Qt.DisplayRole, QtCore.Qt.InitialSortOrderRole
            ):
                role = ITEM_CREATED_AT_ROLE

        if col != 0:
            index = self.index(index.row(), 0, index.parent())

        return super(LoadedFilesModel, self).data(index, role)

    def setData(self, index, value, role=None):
        if role is None:
            role = QtCore.Qt.EditRole

        if role == QtCore.Qt.EditRole:
            item_id = index.data(ITEM_ID_ROLE)
            report_item = self._report_items_by_id.get(item_id)
            if report_item is not None:
                report_item.label = value
                report_item.save()
                value = report_item.label

        return super(LoadedFilesModel, self).setData(index, value, role)

    def flags(self, index):
        # Allow editable flag only for first column
        if index.column() > 0:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        return super(LoadedFilesModel, self).flags(index)

    def _create_item(self, report_item):
        if report_item.id in self._items_by_id:
            return None

        item = QtGui.QStandardItem(report_item.label)
        item.setColumnCount(self.columnCount())
        item.setData(report_item.id, ITEM_ID_ROLE)
        item.setData(report_item.created_at, ITEM_CREATED_AT_ROLE)

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
            report_item = PublishReportItem.from_filepath(normalized_path)
            if report_item is None:
                continue

            # Skip already added report items
            # QUESTION: Should we replace existing or skip the item?
            if report_item.id in self._items_by_id:
                continue

            if not report_item.loaded_label:
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
        self._handler.remove_report_item(item_id)

        self._report_items_by_id.pop(item_id, None)
        item = self._items_by_id.pop(item_id, None)
        if item is not None:
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
            QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.SelectedClicked
            | QtWidgets.QAbstractItemView.DoubleClicked
        )
        self.setIndentation(0)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

        model = LoadedFilesModel()
        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setSourceModel(model)
        self.setModel(proxy_model)

        time_delegate = PrettyTimeDelegate()
        self.setItemDelegateForColumn(1, time_delegate)

        self.sortByColumn(1, QtCore.Qt.AscendingOrder)

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
        self._proxy_model = proxy_model
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
        header.resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        self._update_remove_btn()

    def resizeEvent(self, event):
        super(LoadedFilesView, self).resizeEvent(event)
        self._update_remove_btn()

    def showEvent(self, event):
        super(LoadedFilesView, self).showEvent(event)
        self._model.refresh()
        header = self.header()
        header.resizeSections(QtWidgets.QHeaderView.ResizeToContents)
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

        model = self.model()
        index = model.index(0, 0)
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
