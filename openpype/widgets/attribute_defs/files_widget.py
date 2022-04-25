import os
import collections
import uuid
import clique
import six
from Qt import QtWidgets, QtCore, QtGui

from openpype.lib import FileDefItem
from openpype.tools.utils import paint_image_with_color
# TODO change imports
from openpype.tools.resources import (
    get_pixmap,
    get_image,
)
from openpype.tools.utils import (
    IconButton,
    PixmapLabel
)

ITEM_ID_ROLE = QtCore.Qt.UserRole + 1
ITEM_LABEL_ROLE = QtCore.Qt.UserRole + 2
ITEM_ICON_ROLE = QtCore.Qt.UserRole + 3
FILENAMES_ROLE = QtCore.Qt.UserRole + 4
DIRPATH_ROLE = QtCore.Qt.UserRole + 5
IS_DIR_ROLE = QtCore.Qt.UserRole + 6
EXT_ROLE = QtCore.Qt.UserRole + 7


class DropEmpty(QtWidgets.QWidget):
    _drop_enabled_text = "Drag & Drop\n(drop files here)"

    def __init__(self, parent):
        super(DropEmpty, self).__init__(parent)
        label_widget = QtWidgets.QLabel(self._drop_enabled_text, self)
        label_widget.setAlignment(QtCore.Qt.AlignCenter)

        label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addSpacing(10)
        layout.addWidget(
            label_widget,
            alignment=QtCore.Qt.AlignCenter
        )
        layout.addSpacing(10)

        self._label_widget = label_widget

    def paintEvent(self, event):
        super(DropEmpty, self).paintEvent(event)
        painter = QtGui.QPainter(self)
        pen = QtGui.QPen()
        pen.setWidth(1)
        pen.setBrush(QtCore.Qt.darkGray)
        pen.setStyle(QtCore.Qt.DashLine)
        painter.setPen(pen)
        content_margins = self.layout().contentsMargins()

        left_m = content_margins.left()
        top_m = content_margins.top()
        rect = QtCore.QRect(
            left_m,
            top_m,
            (
                self.rect().width()
                - (left_m + content_margins.right() + pen.width())
            ),
            (
                self.rect().height()
                - (top_m + content_margins.bottom() + pen.width())
            )
        )
        painter.drawRect(rect)


class FilesModel(QtGui.QStandardItemModel):
    def __init__(self, single_item, sequence_exts):
        super(FilesModel, self).__init__()

        self._single_item = single_item
        self._sequence_exts = sequence_exts

        self._items_by_id = {}
        self._file_items_by_id = {}
        self._filenames_by_dirpath = collections.defaultdict(set)
        self._items_by_dirpath = collections.defaultdict(list)

    def add_filepaths(self, items):
        if not items:
            return

        obj_items = FileDefItem.from_value(items, self._sequence_exts)
        if not obj_items:
            return

        if self._single_item:
            obj_items = [obj_items[0]]
            current_ids = list(self._file_items_by_id.keys())
            if current_ids:
                self.remove_item_by_ids(current_ids)

        new_model_items = []
        for obj_item in obj_items:
            _, ext = os.path.splitext(obj_item.filenames[0])
            if ext:
                icon_pixmap = get_pixmap(filename="file.png")
            else:
                icon_pixmap = get_pixmap(filename="folder.png")

            item_id, model_item = self._create_item(obj_item, icon_pixmap)
            new_model_items.append(model_item)
            self._file_items_by_id[item_id] = obj_item
            self._items_by_id[item_id] = model_item

        if new_model_items:
            self.invisibleRootItem().appendRows(new_model_items)

    def remove_item_by_ids(self, item_ids):
        if not item_ids:
            return

        items = []
        for item_id in set(item_ids):
            if item_id not in self._items_by_id:
                continue
            item = self._items_by_id.pop(item_id)
            self._file_items_by_id.pop(item_id)
            items.append(item)

        if items:
            for item in items:
                self.removeRows(item.row(), 1)

    def get_file_item_by_id(self, item_id):
        return self._file_items_by_id.get(item_id)

    def _create_item(self, file_item, icon_pixmap=None):
        item = QtGui.QStandardItem()
        item_id = str(uuid.uuid4())
        item.setData(item_id, ITEM_ID_ROLE)
        item.setData(file_item.label, ITEM_LABEL_ROLE)
        item.setData(file_item.filenames, FILENAMES_ROLE)
        item.setData(file_item.directory, DIRPATH_ROLE)
        item.setData(icon_pixmap, ITEM_ICON_ROLE)
        item.setData(file_item.ext, EXT_ROLE)
        item.setData(file_item.is_dir, IS_DIR_ROLE)

        return item_id, item


class FilesProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        super(FilesProxyModel, self).__init__(*args, **kwargs)
        self._allow_folders = False
        self._allowed_extensions = None

    def set_allow_folders(self, allow=None):
        if allow is None:
            allow = not self._allow_folders

        if allow == self._allow_folders:
            return
        self._allow_folders = allow
        self.invalidateFilter()

    def set_allowed_extensions(self, extensions=None):
        if extensions is not None:
            extensions = set(extensions)

        if self._allowed_extensions != extensions:
            self._allowed_extensions = extensions
            self.invalidateFilter()

    def are_valid_files(self, filepaths):
        for filepath in filepaths:
            if os.path.isfile(filepath):
                _, ext = os.path.splitext(filepath)
                if ext in self._allowed_extensions:
                    return True

            elif self._allow_folders:
                return True
        return False

    def filterAcceptsRow(self, row, parent_index):
        model = self.sourceModel()
        index = model.index(row, self.filterKeyColumn(), parent_index)
        # First check if item is folder and if folders are enabled
        if index.data(IS_DIR_ROLE):
            if not self._allow_folders:
                return False
            return True

        # Check if there are any allowed extensions
        if self._allowed_extensions is None:
            return False

        if index.data(EXT_ROLE) not in self._allowed_extensions:
            return False
        return True

    def lessThan(self, left, right):
        left_comparison = left.data(DIRPATH_ROLE)
        right_comparison = right.data(DIRPATH_ROLE)
        if left_comparison == right_comparison:
            left_comparison = left.data(ITEM_LABEL_ROLE)
            right_comparison = right.data(ITEM_LABEL_ROLE)

        if sorted((left_comparison, right_comparison))[0] == left_comparison:
            return True
        return False


class ItemWidget(QtWidgets.QWidget):
    remove_requested = QtCore.Signal(str)

    def __init__(self, item_id, label, pixmap_icon, parent=None):
        self._item_id = item_id

        super(ItemWidget, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        icon_widget = PixmapLabel(pixmap_icon, self)
        label_widget = QtWidgets.QLabel(label, self)
        pixmap = paint_image_with_color(
            get_image(filename="delete.png"), QtCore.Qt.white
        )
        remove_btn = IconButton(self)
        remove_btn.setIcon(QtGui.QIcon(pixmap))

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(icon_widget, 0)
        layout.addWidget(label_widget, 1)
        layout.addWidget(remove_btn, 0)

        remove_btn.clicked.connect(self._on_remove_clicked)

        self._icon_widget = icon_widget
        self._label_widget = label_widget
        self._remove_btn = remove_btn

    def _on_remove_clicked(self):
        self.remove_requested.emit(self._item_id)


class FilesView(QtWidgets.QListView):
    """View showing instances and their groups."""

    def __init__(self, *args, **kwargs):
        super(FilesView, self).__init__(*args, **kwargs)

        self.setEditTriggers(QtWidgets.QListView.NoEditTriggers)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )

    def get_selected_item_ids(self):
        """Ids of selected instances."""
        selected_item_ids = set()
        for index in self.selectionModel().selectedIndexes():
            instance_id = index.data(ITEM_ID_ROLE)
            if instance_id is not None:
                selected_item_ids.add(instance_id)
        return selected_item_ids

    def event(self, event):
        if not event.type() == QtCore.QEvent.KeyPress:
            pass

        elif event.key() == QtCore.Qt.Key_Space:
            self.toggle_requested.emit(-1)
            return True

        elif event.key() == QtCore.Qt.Key_Backspace:
            self.toggle_requested.emit(0)
            return True

        elif event.key() == QtCore.Qt.Key_Return:
            self.toggle_requested.emit(1)
            return True

        return super(FilesView, self).event(event)


class FilesWidget(QtWidgets.QFrame):
    value_changed = QtCore.Signal()

    def __init__(self, single_item, sequence_exts, parent):
        super(FilesWidget, self).__init__(parent)
        self.setAcceptDrops(True)

        empty_widget = DropEmpty(self)

        files_model = FilesModel(single_item, sequence_exts)
        files_proxy_model = FilesProxyModel()
        files_proxy_model.setSourceModel(files_model)
        files_view = FilesView(self)
        files_view.setModel(files_proxy_model)
        files_view.setVisible(False)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(empty_widget, 1)
        layout.addWidget(files_view, 1)

        files_proxy_model.rowsInserted.connect(self._on_rows_inserted)
        files_proxy_model.rowsRemoved.connect(self._on_rows_removed)

        self._in_set_value = False

        self._empty_widget = empty_widget
        self._files_model = files_model
        self._files_proxy_model = files_proxy_model
        self._files_view = files_view

        self._widgets_by_id = {}

    def set_value(self, value, multivalue):
        self._in_set_value = True
        widget_ids = set(self._widgets_by_id.keys())
        self._remove_item_by_ids(widget_ids)

        # TODO how to display multivalue?
        all_same = True
        if multivalue:
            new_value = set()
            item_row = None
            for _value in value:
                _value_set = set(_value)
                new_value |= _value_set
                if item_row is None:
                    item_row = _value_set
                elif item_row != _value_set:
                    all_same = False
            value = new_value

        if value:
            self._add_filepaths(value)
        self._in_set_value = False

    def current_value(self):
        model = self._files_proxy_model
        item_ids = set()
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            item_ids.add(index.data(ITEM_ID_ROLE))

        file_items = []
        for item_id in item_ids:
            file_item = self._files_model.get_file_item_by_id(item_id)
            if file_item is not None:
                file_items.append(file_item.to_dict())
        return file_items

    def set_filters(self, folders_allowed, exts_filter):
        self._files_proxy_model.set_allow_folders(folders_allowed)
        self._files_proxy_model.set_allowed_extensions(exts_filter)

    def _on_rows_inserted(self, parent_index, start_row, end_row):
        for row in range(start_row, end_row + 1):
            index = self._files_proxy_model.index(row, 0, parent_index)
            item_id = index.data(ITEM_ID_ROLE)
            if item_id in self._widgets_by_id:
                continue
            label = index.data(ITEM_LABEL_ROLE)
            pixmap_icon = index.data(ITEM_ICON_ROLE)

            widget = ItemWidget(item_id, label, pixmap_icon)
            self._files_view.setIndexWidget(index, widget)
            self._files_proxy_model.setData(
                index, widget.sizeHint(), QtCore.Qt.SizeHintRole
            )
            widget.remove_requested.connect(self._on_remove_request)
            self._widgets_by_id[item_id] = widget

        self._files_proxy_model.sort(0)

        if not self._in_set_value:
            self.value_changed.emit()

    def _on_rows_removed(self, parent_index, start_row, end_row):
        available_item_ids = set()
        for row in range(self._files_proxy_model.rowCount()):
            index = self._files_proxy_model.index(row, 0)
            item_id = index.data(ITEM_ID_ROLE)
            available_item_ids.add(index.data(ITEM_ID_ROLE))

        widget_ids = set(self._widgets_by_id.keys())
        for item_id in available_item_ids:
            if item_id in widget_ids:
                widget_ids.remove(item_id)

        for item_id in widget_ids:
            widget = self._widgets_by_id.pop(item_id)
            widget.setVisible(False)
            widget.deleteLater()

        if not self._in_set_value:
            self.value_changed.emit()

    def _on_remove_request(self, item_id):
        found_index = None
        for row in range(self._files_model.rowCount()):
            index = self._files_model.index(row, 0)
            _item_id = index.data(ITEM_ID_ROLE)
            if item_id == _item_id:
                found_index = index
                break

        if found_index is None:
            return

        items_to_delete = self._files_view.get_selected_item_ids()
        if item_id not in items_to_delete:
            items_to_delete = [item_id]

        self._remove_item_by_ids(items_to_delete)

    def sizeHint(self):
        # Get size hints of widget and visible widgets
        result = super(FilesWidget, self).sizeHint()
        if not self._files_view.isVisible():
            not_visible_hint = self._files_view.sizeHint()
        else:
            not_visible_hint = self._empty_widget.sizeHint()

        # Get margins of this widget
        margins = self.layout().contentsMargins()

        # Change size hint based on result of maximum size hint of widgets
        result.setWidth(max(
            result.width(),
            not_visible_hint.width() + margins.left() + margins.right()
        ))
        result.setHeight(max(
            result.height(),
            not_visible_hint.height() + margins.top() + margins.bottom()
        ))

        return result

    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            filepaths = []
            for url in mime_data.urls():
                filepath = url.toLocalFile()
                if os.path.exists(filepath):
                    filepaths.append(filepath)

            if self._files_proxy_model.are_valid_files(filepaths):
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
                if os.path.exists(filepath):
                    filepaths.append(filepath)
            if filepaths:
                self._add_filepaths(filepaths)
        event.accept()

    def _add_filepaths(self, filepaths):
        self._files_model.add_filepaths(filepaths)
        self._update_visibility()

    def _remove_item_by_ids(self, item_ids):
        self._files_model.remove_item_by_ids(item_ids)
        self._update_visibility()

    def _update_visibility(self):
        files_exists = self._files_proxy_model.rowCount() > 0
        self._files_view.setVisible(files_exists)
        self._empty_widget.setVisible(not files_exists)
