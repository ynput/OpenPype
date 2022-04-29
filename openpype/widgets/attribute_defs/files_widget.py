import os
import collections
import uuid

from Qt import QtWidgets, QtCore, QtGui

from openpype.lib import FileDefItem
from openpype.tools.utils import (
    paint_image_with_color,
    ClickableLabel,
)
# TODO change imports
from openpype.tools.resources import get_image
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
IS_SEQUENCE_ROLE = QtCore.Qt.UserRole + 7
EXT_ROLE = QtCore.Qt.UserRole + 8


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
    def __init__(self, single_item, allow_sequences):
        super(FilesModel, self).__init__()

        self._single_item = single_item
        self._multivalue = False
        self._allow_sequences = allow_sequences

        self._items_by_id = {}
        self._file_items_by_id = {}
        self._filenames_by_dirpath = collections.defaultdict(set)
        self._items_by_dirpath = collections.defaultdict(list)

    def set_multivalue(self, multivalue):
        """Disable filtering."""

        if self._multivalue == multivalue:
            return
        self._multivalue = multivalue

    def add_filepaths(self, items):
        if not items:
            return

        file_items = FileDefItem.from_value(items, self._allow_sequences)
        if not file_items:
            return

        if not self._multivalue and self._single_item:
            file_items = [file_items[0]]
            current_ids = list(self._file_items_by_id.keys())
            if current_ids:
                self.remove_item_by_ids(current_ids)

        new_model_items = []
        for file_item in file_items:
            item_id, model_item = self._create_item(file_item)
            new_model_items.append(model_item)
            self._file_items_by_id[item_id] = file_item
            self._items_by_id[item_id] = model_item

        if new_model_items:
            roow_item = self.invisibleRootItem()
            roow_item.appendRows(new_model_items)

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

    def _create_item(self, file_item):
        if file_item.is_dir:
            icon_pixmap = paint_image_with_color(
                get_image(filename="folder.png"), QtCore.Qt.white
            )
        else:
            icon_pixmap = paint_image_with_color(
                get_image(filename="file.png"), QtCore.Qt.white
            )

        item = QtGui.QStandardItem()
        item_id = str(uuid.uuid4())
        item.setData(item_id, ITEM_ID_ROLE)
        item.setData(file_item.label, ITEM_LABEL_ROLE)
        item.setData(file_item.filenames, FILENAMES_ROLE)
        item.setData(file_item.directory, DIRPATH_ROLE)
        item.setData(icon_pixmap, ITEM_ICON_ROLE)
        item.setData(file_item.ext, EXT_ROLE)
        item.setData(file_item.is_dir, IS_DIR_ROLE)
        item.setData(file_item.is_sequence, IS_SEQUENCE_ROLE)

        return item_id, item


class FilesProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        super(FilesProxyModel, self).__init__(*args, **kwargs)
        self._allow_folders = False
        self._allowed_extensions = None
        self._multivalue = False

    def set_multivalue(self, multivalue):
        """Disable filtering."""

        if self._multivalue == multivalue:
            return
        self._multivalue = multivalue
        self.invalidateFilter()

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

    def filter_valid_files(self, filepaths):
        filtered_paths = []
        for filepath in filepaths:
            if os.path.isfile(filepath):
                _, ext = os.path.splitext(filepath)
                if ext in self._allowed_extensions:
                    filtered_paths.append(filepath)

            elif self._allow_folders:
                filtered_paths.append(filepath)
        return filtered_paths

    def filterAcceptsRow(self, row, parent_index):
        # Skip filtering if multivalue is set
        if self._multivalue:
            return True

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
    context_menu_requested = QtCore.Signal(QtCore.QPoint)

    def __init__(
        self, item_id, label, pixmap_icon, is_sequence, multivalue, parent=None
    ):
        self._item_id = item_id

        super(ItemWidget, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        icon_widget = PixmapLabel(pixmap_icon, self)
        label_widget = QtWidgets.QLabel(label, self)

        label_size_hint = label_widget.sizeHint()
        height = label_size_hint.height()
        actions_menu_pix = paint_image_with_color(
            get_image(filename="menu.png"), QtCore.Qt.white
        )

        split_btn = ClickableLabel(self)
        split_btn.setFixedSize(height, height)
        split_btn.setPixmap(actions_menu_pix)
        if multivalue:
            split_btn.setVisible(False)
        else:
            split_btn.setVisible(is_sequence)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(icon_widget, 0)
        layout.addWidget(label_widget, 1)
        layout.addWidget(split_btn, 0)

        split_btn.clicked.connect(self._on_actions_clicked)

        self._icon_widget = icon_widget
        self._label_widget = label_widget
        self._split_btn = split_btn
        self._actions_menu_pix = actions_menu_pix
        self._last_scaled_pix_height = None

    def _update_btn_size(self):
        label_size_hint = self._label_widget.sizeHint()
        height = label_size_hint.height()
        if height == self._last_scaled_pix_height:
            return
        self._last_scaled_pix_height = height
        self._split_btn.setFixedSize(height, height)
        pix = self._actions_menu_pix.scaled(
            height, height,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        self._split_btn.setPixmap(pix)

    def showEvent(self, event):
        super(ItemWidget, self).showEvent(event)
        self._update_btn_size()

    def resizeEvent(self, event):
        super(ItemWidget, self).resizeEvent(event)
        self._update_btn_size()

    def _on_actions_clicked(self):
        pos = self._split_btn.rect().bottomLeft()
        point = self._split_btn.mapToGlobal(pos)
        self.context_menu_requested.emit(point)


class InViewButton(IconButton):
    pass


class FilesView(QtWidgets.QListView):
    """View showing instances and their groups."""

    remove_requested = QtCore.Signal()
    context_menu_requested = QtCore.Signal(QtCore.QPoint)

    def __init__(self, *args, **kwargs):
        super(FilesView, self).__init__(*args, **kwargs)

        self.setEditTriggers(QtWidgets.QListView.NoEditTriggers)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        remove_btn = InViewButton(self)
        pix_enabled = paint_image_with_color(
            get_image(filename="delete.png"), QtCore.Qt.white
        )
        pix_disabled = paint_image_with_color(
            get_image(filename="delete.png"), QtCore.Qt.gray
        )
        icon = QtGui.QIcon(pix_enabled)
        icon.addPixmap(pix_disabled, icon.Disabled, icon.Off)
        remove_btn.setIcon(icon)
        remove_btn.setEnabled(False)

        remove_btn.clicked.connect(self._on_remove_clicked)
        self.customContextMenuRequested.connect(self._on_context_menu_request)

        self._remove_btn = remove_btn

    def setSelectionModel(self, *args, **kwargs):
        """Catch selection model set to register signal callback.

        Selection model is not available during initialization.
        """

        super(FilesView, self).setSelectionModel(*args, **kwargs)
        selection_model = self.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_change)

    def set_multivalue(self, multivalue):
        """Disable remove button on multivalue."""

        self._remove_btn.setVisible(not multivalue)

    def has_selected_item_ids(self):
        """Is any index selected."""
        for index in self.selectionModel().selectedIndexes():
            instance_id = index.data(ITEM_ID_ROLE)
            if instance_id is not None:
                return True
        return False

    def get_selected_item_ids(self):
        """Ids of selected instances."""

        selected_item_ids = set()
        for index in self.selectionModel().selectedIndexes():
            instance_id = index.data(ITEM_ID_ROLE)
            if instance_id is not None:
                selected_item_ids.add(instance_id)
        return selected_item_ids

    def has_selected_sequence(self):
        for index in self.selectionModel().selectedIndexes():
            if index.data(IS_SEQUENCE_ROLE):
                return True
        return False

    def event(self, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if (
                event.key() == QtCore.Qt.Key_Delete
                and self.has_selected_item_ids()
            ):
                self.remove_requested.emit()
                return True

        return super(FilesView, self).event(event)

    def _on_context_menu_request(self, pos):
        index = self.indexAt(pos)
        if index.isValid():
            point = self.viewport().mapToGlobal(pos)
            self.context_menu_requested.emit(point)

    def _on_selection_change(self):
        self._remove_btn.setEnabled(self.has_selected_item_ids())

    def _on_remove_clicked(self):
        self.remove_requested.emit()

    def _update_remove_btn(self):
        """Position remove button to bottom right."""

        viewport = self.viewport()
        height = viewport.height()
        pos_x = viewport.width() - self._remove_btn.width() - 5
        pos_y = height - self._remove_btn.height() - 5
        self._remove_btn.move(max(0, pos_x), max(0, pos_y))

    def resizeEvent(self, event):
        super(FilesView, self).resizeEvent(event)
        self._update_remove_btn()

    def showEvent(self, event):
        super(FilesView, self).showEvent(event)
        self._update_remove_btn()


class FilesWidget(QtWidgets.QFrame):
    value_changed = QtCore.Signal()

    def __init__(self, single_item, allow_sequences, parent):
        super(FilesWidget, self).__init__(parent)
        self.setAcceptDrops(True)

        empty_widget = DropEmpty(self)

        files_model = FilesModel(single_item, allow_sequences)
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
        files_view.remove_requested.connect(self._on_remove_requested)
        files_view.context_menu_requested.connect(
            self._on_context_menu_requested
        )
        self._in_set_value = False
        self._single_item = single_item
        self._multivalue = False

        self._empty_widget = empty_widget
        self._files_model = files_model
        self._files_proxy_model = files_proxy_model
        self._files_view = files_view

        self._widgets_by_id = {}

    def _set_multivalue(self, multivalue):
        if self._multivalue == multivalue:
            return
        self._multivalue = multivalue
        self._files_view.set_multivalue(multivalue)
        self._files_model.set_multivalue(multivalue)
        self._files_proxy_model.set_multivalue(multivalue)

    def set_value(self, value, multivalue):
        self._in_set_value = True

        widget_ids = set(self._widgets_by_id.keys())
        self._remove_item_by_ids(widget_ids)

        self._set_multivalue(multivalue)

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

        if not self._single_item:
            return file_items
        if file_items:
            return file_items[0]
        return FileDefItem.create_empty_item()

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
            is_sequence = index.data(IS_SEQUENCE_ROLE)

            widget = ItemWidget(
                item_id,
                label,
                pixmap_icon,
                is_sequence,
                self._multivalue
            )
            widget.context_menu_requested.connect(
                self._on_context_menu_requested
            )
            self._files_view.setIndexWidget(index, widget)
            self._files_proxy_model.setData(
                index, widget.sizeHint(), QtCore.Qt.SizeHintRole
            )
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

    def _on_split_request(self):
        if self._multivalue:
            return

        item_ids = self._files_view.get_selected_item_ids()
        if not item_ids:
            return

        for item_id in item_ids:
            file_item = self._files_model.get_file_item_by_id(item_id)
            if not file_item:
                return

            new_items = file_item.split_sequence()
            self._add_filepaths(new_items)
        self._remove_item_by_ids(item_ids)

    def _on_remove_requested(self):
        if self._multivalue:
            return

        items_to_delete = self._files_view.get_selected_item_ids()
        if items_to_delete:
            self._remove_item_by_ids(items_to_delete)

    def _on_context_menu_requested(self, pos):
        if self._multivalue:
            return

        menu = QtWidgets.QMenu(self._files_view)

        if self._files_view.has_selected_sequence():
            split_action = QtWidgets.QAction("Split sequence", menu)
            split_action.triggered.connect(self._on_split_request)
            menu.addAction(split_action)

        remove_action = QtWidgets.QAction("Remove", menu)
        remove_action.triggered.connect(self._on_remove_requested)
        menu.addAction(remove_action)

        menu.popup(pos)

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
        if self._multivalue:
            return

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
        if not self._multivalue and mime_data.hasUrls():
            filepaths = []
            for url in mime_data.urls():
                filepath = url.toLocalFile()
                if os.path.exists(filepath):
                    filepaths.append(filepath)

            # Filter filepaths before passing it to model
            filepaths = self._files_proxy_model.filter_valid_files(filepaths)
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
