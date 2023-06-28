import os
import collections
import uuid
import json

from qtpy import QtWidgets, QtCore, QtGui

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


def convert_bytes_to_json(bytes_value):
    if isinstance(bytes_value, QtCore.QByteArray):
        # Raw data are already QByteArray and we don't have to load them
        encoded_data = bytes_value
    else:
        encoded_data = QtCore.QByteArray.fromRawData(bytes_value)
    stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.ReadOnly)
    text = stream.readQString()
    try:
        return json.loads(text)
    except Exception:
        return None


def convert_data_to_bytes(data):
    bytes_value = QtCore.QByteArray()
    stream = QtCore.QDataStream(bytes_value, QtCore.QIODevice.WriteOnly)
    stream.writeQString(json.dumps(data))
    return bytes_value


class SupportLabel(QtWidgets.QLabel):
    pass


class DropEmpty(QtWidgets.QWidget):
    _empty_extensions = "Any file"

    def __init__(self, single_item, allow_sequences, extensions_label, parent):
        super(DropEmpty, self).__init__(parent)

        drop_label_widget = QtWidgets.QLabel("Drag & Drop files here", self)

        items_label_widget = SupportLabel(self)
        items_label_widget.setWordWrap(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addSpacing(20)
        layout.addWidget(
            drop_label_widget, 0, alignment=QtCore.Qt.AlignCenter
        )
        layout.addSpacing(30)
        layout.addStretch(1)
        layout.addWidget(
            items_label_widget, 0, alignment=QtCore.Qt.AlignCenter
        )
        layout.addSpacing(10)

        for widget in (
            drop_label_widget,
            items_label_widget,
        ):
            widget.setAlignment(QtCore.Qt.AlignCenter)
            widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        update_size_timer = QtCore.QTimer()
        update_size_timer.setInterval(10)
        update_size_timer.setSingleShot(True)

        update_size_timer.timeout.connect(self._on_update_size_timer)

        self._update_size_timer = update_size_timer

        if extensions_label and not extensions_label.startswith(" "):
            extensions_label = " " + extensions_label

        self._single_item = single_item
        self._extensions_label = extensions_label
        self._allow_sequences = allow_sequences
        self._allowed_extensions = set()
        self._allow_folders = None

        self._drop_label_widget = drop_label_widget
        self._items_label_widget = items_label_widget

        self.set_allow_folders(False)

    def set_extensions(self, extensions):
        if extensions:
            extensions = {
                ext.replace(".", "")
                for ext in extensions
            }
        if extensions == self._allowed_extensions:
            return
        self._allowed_extensions = extensions

        self._update_items_label()

    def set_allow_folders(self, allowed):
        if self._allow_folders == allowed:
            return

        self._allow_folders = allowed
        self._update_items_label()

    def _update_items_label(self):
        allowed_items = []
        if self._allow_folders:
            allowed_items.append("folder")

        if self._allowed_extensions:
            allowed_items.append("file")
            if self._allow_sequences:
                allowed_items.append("sequence")

        if not self._single_item:
            allowed_items = [item + "s" for item in allowed_items]

        if not allowed_items:
            self._drop_label_widget.setVisible(False)
            self._items_label_widget.setText(
                "It is not allowed to add anything here!"
            )
            return

        self._drop_label_widget.setVisible(True)
        items_label = "Multiple "
        if self._single_item:
            items_label = "Single "

        if len(allowed_items) == 1:
            extensions_label = allowed_items[0]
        elif len(allowed_items) == 2:
            extensions_label = " or ".join(allowed_items)
        else:
            last_item = allowed_items.pop(-1)
            new_last_item = " or ".join([last_item, allowed_items.pop(-1)])
            allowed_items.append(new_last_item)
            extensions_label = ", ".join(allowed_items)

        allowed_items_label = extensions_label

        items_label += allowed_items_label
        label_tooltip = None
        if self._allowed_extensions:
            items_label += " of\n{}".format(
                ", ".join(sorted(self._allowed_extensions))
            )

        if self._extensions_label:
            label_tooltip = items_label
            items_label = self._extensions_label

        if self._items_label_widget.text() == items_label:
            return

        self._items_label_widget.setToolTip(label_tooltip)
        self._items_label_widget.setText(items_label)
        self._update_size_timer.start()

    def resizeEvent(self, event):
        super(DropEmpty, self).resizeEvent(event)
        self._update_size_timer.start()

    def _on_update_size_timer(self):
        """Recalculate height of label with extensions.

        Dynamic QLabel with word wrap does not handle properly it's sizeHint
        calculations on show. This way it is recalculated. It is good practice
        to trigger this method with small offset using '_update_size_timer'.
        """

        width = self._items_label_widget.width()
        height = self._items_label_widget.heightForWidth(width)
        self._items_label_widget.setMinimumHeight(height)
        self._items_label_widget.updateGeometry()

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

        self._id = str(uuid.uuid4())
        self._single_item = single_item
        self._multivalue = False
        self._allow_sequences = allow_sequences

        self._items_by_id = {}
        self._file_items_by_id = {}
        self._filenames_by_dirpath = collections.defaultdict(set)
        self._items_by_dirpath = collections.defaultdict(list)

        self.rowsAboutToBeRemoved.connect(self._on_about_to_be_removed)
        self.rowsInserted.connect(self._on_insert)

    @property
    def id(self):
        return self._id

    def _on_about_to_be_removed(self, parent_index, start, end):
        """Make sure that removed items are removed from items mapping.

        Connected with '_on_insert'. When user drag item and drop it to same
        view the item is actually removed and creted again but it happens in
        inner calls of Qt.
        """

        for row in range(start, end + 1):
            index = self.index(row, 0, parent_index)
            item_id = index.data(ITEM_ID_ROLE)
            if item_id is not None:
                self._items_by_id.pop(item_id, None)

    def _on_insert(self, parent_index, start, end):
        """Make sure new added items are stored in items mapping.

        Connected to '_on_about_to_be_removed'. Some items are not created
        using '_create_item' but are recreated using Qt. So the item is not in
        mapping and if it would it would not lead to same item pointer.
        """

        for row in range(start, end + 1):
            index = self.index(start, end, parent_index)
            item_id = index.data(ITEM_ID_ROLE)
            if item_id not in self._items_by_id:
                self._items_by_id[item_id] = self.item(row)

    def set_multivalue(self, multivalue):
        """Disable filtering."""

        if self._multivalue == multivalue:
            return
        self._multivalue = multivalue

    def add_filepaths(self, items):
        if not items:
            return

        if self._multivalue:
            _items = []
            for item in items:
                if isinstance(item, (tuple, list, set)):
                    _items.extend(item)
                else:
                    _items.append(item)
            items = _items

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
        item.setData(file_item.label or "< empty >", ITEM_LABEL_ROLE)
        item.setData(file_item.filenames, FILENAMES_ROLE)
        item.setData(file_item.directory, DIRPATH_ROLE)
        item.setData(icon_pixmap, ITEM_ICON_ROLE)
        item.setData(file_item.lower_ext, EXT_ROLE)
        item.setData(file_item.is_dir, IS_DIR_ROLE)
        item.setData(file_item.is_sequence, IS_SEQUENCE_ROLE)

        return item_id, item

    def mimeData(self, indexes):
        item_ids = [
            index.data(ITEM_ID_ROLE)
            for index in indexes
        ]

        item_ids_data = convert_data_to_bytes(item_ids)
        mime_data = super(FilesModel, self).mimeData(indexes)
        mime_data.setData("files_widget/internal_move", item_ids_data)

        file_items = []
        for item_id in item_ids:
            file_item = self.get_file_item_by_id(item_id)
            if file_item:
                file_items.append(file_item.to_dict())

        full_item_data = convert_data_to_bytes({
            "items": file_items,
            "id": self._id
        })
        mime_data.setData("files_widget/full_data", full_item_data)
        return mime_data

    def dropMimeData(self, mime_data, action, row, col, index):
        item_ids = convert_bytes_to_json(
            mime_data.data("files_widget/internal_move")
        )
        if item_ids is None:
            return False

        # Find matching item after which will be items moved
        #   - store item before moved items are removed
        root = self.invisibleRootItem()
        if row >= 0:
            src_item = self.item(row)
        else:
            src_item_id = index.data(ITEM_ID_ROLE)
            src_item = self._items_by_id.get(src_item_id)

        src_row = None
        if src_item:
            src_row = src_item.row()

        # Take out items that should be moved
        items = []
        for item_id in item_ids:
            item = self._items_by_id.get(item_id)
            if item:
                self.takeRow(item.row())
                items.append(item)

        # Skip if there are not items that can be moved
        if not items:
            return False

        # Calculate row where items should be inserted
        row_count = root.rowCount()
        if src_row is None:
            src_row = row_count

        if src_row > row_count:
            src_row = row_count

        root.insertRow(src_row, items)
        return True


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
            _extensions = set()
            for ext in set(extensions):
                if not ext.startswith("."):
                    ext = ".{}".format(ext)
                _extensions.add(ext.lower())
            extensions = _extensions

        if self._allowed_extensions != extensions:
            self._allowed_extensions = extensions
            self.invalidateFilter()

    def are_valid_files(self, filepaths):
        for filepath in filepaths:
            if os.path.isfile(filepath):
                _, ext = os.path.splitext(filepath)
                if ext.lower() in self._allowed_extensions:
                    return True

            elif self._allow_folders:
                return True
        return False

    def filter_valid_files(self, filepaths):
        filtered_paths = []
        for filepath in filepaths:
            if os.path.isfile(filepath):
                _, ext = os.path.splitext(filepath)
                if ext.lower() in self._allowed_extensions:
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

        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

        remove_btn = InViewButton(self)
        pix_enabled = paint_image_with_color(
            get_image(filename="delete.png"), QtCore.Qt.white
        )
        pix_disabled = paint_image_with_color(
            get_image(filename="delete.png"), QtCore.Qt.gray
        )
        icon = QtGui.QIcon(pix_enabled)
        icon.addPixmap(pix_disabled, QtGui.QIcon.Disabled, QtGui.QIcon.Off)
        remove_btn.setIcon(icon)
        remove_btn.setEnabled(False)

        remove_btn.clicked.connect(self._on_remove_clicked)
        self.customContextMenuRequested.connect(self._on_context_menu_request)

        self._remove_btn = remove_btn
        self._multivalue = False

    def setSelectionModel(self, *args, **kwargs):
        """Catch selection model set to register signal callback.

        Selection model is not available during initialization.
        """

        super(FilesView, self).setSelectionModel(*args, **kwargs)
        selection_model = self.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_change)

    def set_multivalue(self, multivalue):
        """Disable remove button on multivalue."""

        self._multivalue = multivalue
        self._remove_btn.setVisible(not multivalue)

    def update_remove_btn_visibility(self):
        model = self.model()
        visible = False
        if not self._multivalue and model:
            visible = model.rowCount() > 0
        self._remove_btn.setVisible(visible)

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
        self.update_remove_btn_visibility()


class FilesWidget(QtWidgets.QFrame):
    value_changed = QtCore.Signal()

    def __init__(self, single_item, allow_sequences, extensions_label, parent):
        super(FilesWidget, self).__init__(parent)
        self.setAcceptDrops(True)

        empty_widget = DropEmpty(
            single_item, allow_sequences, extensions_label, self
        )

        files_model = FilesModel(single_item, allow_sequences)
        files_proxy_model = FilesProxyModel()
        files_proxy_model.setSourceModel(files_model)
        files_view = FilesView(self)
        files_view.setModel(files_proxy_model)

        layout = QtWidgets.QStackedLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setStackingMode(QtWidgets.QStackedLayout.StackAll)
        layout.addWidget(empty_widget)
        layout.addWidget(files_view)
        layout.setCurrentWidget(empty_widget)

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

        self._layout = layout

    def _set_multivalue(self, multivalue):
        if self._multivalue is multivalue:
            return
        self._multivalue = multivalue
        self._files_view.set_multivalue(multivalue)
        self._files_model.set_multivalue(multivalue)
        self._files_proxy_model.set_multivalue(multivalue)
        self.setEnabled(not multivalue)

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

        empty_item = FileDefItem.create_empty_item()
        return empty_item.to_dict()

    def set_filters(self, folders_allowed, exts_filter):
        self._files_proxy_model.set_allow_folders(folders_allowed)
        self._files_proxy_model.set_allowed_extensions(exts_filter)
        self._empty_widget.set_extensions(exts_filter)
        self._empty_widget.set_allow_folders(folders_allowed)

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

        if not self._in_set_value:
            self.value_changed.emit()

        self._update_visibility()

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
        self._update_visibility()

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

        full_data_value = mime_data.data("files_widget/full_data")
        if self._handle_full_data_drag(full_data_value):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()

    def dragLeaveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        if self._multivalue:
            return

        mime_data = event.mimeData()
        if mime_data.hasUrls():
            event.accept()
            filepaths = []
            for url in mime_data.urls():
                filepath = url.toLocalFile()
                if os.path.exists(filepath):
                    filepaths.append(filepath)

            # Filter filepaths before passing it to model
            filepaths = self._files_proxy_model.filter_valid_files(filepaths)
            if filepaths:
                self._add_filepaths(filepaths)

        if self._handle_full_data_drop(
            mime_data.data("files_widget/full_data")
        ):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()

        super(FilesWidget, self).dropEvent(event)

    def _handle_full_data_drag(self, value):
        if value is None:
            return False

        full_data = convert_bytes_to_json(value)
        if full_data is None:
            return False

        if full_data["id"] == self._files_model.id:
            return False
        return True

    def _handle_full_data_drop(self, value):
        if value is None:
            return False

        full_data = convert_bytes_to_json(value)
        if full_data is None:
            return False

        if full_data["id"] == self._files_model.id:
            return False

        for item in full_data["items"]:
            filepaths = [
                os.path.join(item["directory"], filename)
                for filename in item["filenames"]
            ]
            filepaths = self._files_proxy_model.filter_valid_files(filepaths)
            if filepaths:
                self._add_filepaths(filepaths)

        if self._copy_modifiers_enabled():
            return False
        return True

    def _copy_modifiers_enabled(self):
        if (
            QtWidgets.QApplication.keyboardModifiers()
            & QtCore.Qt.ControlModifier
        ):
            return True
        return False

    def _add_filepaths(self, filepaths):
        self._files_model.add_filepaths(filepaths)

    def _remove_item_by_ids(self, item_ids):
        self._files_model.remove_item_by_ids(item_ids)

    def _update_visibility(self):
        files_exists = self._files_proxy_model.rowCount() > 0
        if files_exists:
            current_widget = self._files_view
        else:
            current_widget = self._empty_widget
        self._layout.setCurrentWidget(current_widget)
        self._files_view.update_remove_btn_visibility()
