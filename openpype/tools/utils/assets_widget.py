import collections

import Qt
from Qt import QtWidgets, QtCore, QtGui

from avalon import style
from avalon.vendor import qtawesome

from openpype.style import get_objected_colors

from .lib import DynamicQThread
from .views import (
    TreeViewSpinner,
    DeselectableTreeView
)

if Qt.__binding__ == "PySide":
    from PySide.QtGui import QStyleOptionViewItemV4
elif Qt.__binding__ == "PyQt4":
    from PyQt4.QtGui import QStyleOptionViewItemV4

ASSET_ID_ROLE = QtCore.Qt.UserRole + 1
ASSET_NAME_ROLE = QtCore.Qt.UserRole + 2
ASSET_LABEL_ROLE = QtCore.Qt.UserRole + 3
ASSET_UNDERLINE_COLORS_ROLE = QtCore.Qt.UserRole + 4


class AssetsView(TreeViewSpinner, DeselectableTreeView):
    """Item view.
    This implements a context menu.
    """

    def __init__(self, parent=None):
        super(AssetsView, self).__init__(parent)
        self.setIndentation(15)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setHeaderHidden(True)

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ShiftModifier:
                return
            elif modifiers == QtCore.Qt.ControlModifier:
                return

        super(AssetsView, self).mousePressEvent(event)

    def set_loading_state(self, loading, empty):
        if self.is_loading != loading:
            if loading:
                self.spinner.repaintNeeded.connect(
                    self.viewport().update
                )
            else:
                self.spinner.repaintNeeded.disconnect()
                self.viewport().update()

        self.is_loading = loading
        self.is_empty = empty


class UnderlinesAssetDelegate(QtWidgets.QItemDelegate):
    bar_height = 3

    def __init__(self, *args, **kwargs):
        super(UnderlinesAssetDelegate, self).__init__(*args, **kwargs)
        asset_view_colors = get_objected_colors()["loader"]["asset-view"]
        self._selected_color = (
            asset_view_colors["selected"].get_qcolor()
        )
        self._hover_color = (
            asset_view_colors["hover"].get_qcolor()
        )
        self._selected_hover_color = (
            asset_view_colors["selected-hover"].get_qcolor()
        )

    def sizeHint(self, option, index):
        result = super(UnderlinesAssetDelegate, self).sizeHint(option, index)
        height = result.height()
        result.setHeight(height + self.bar_height)

        return result

    def paint(self, painter, option, index):
        # Qt4 compat
        if Qt.__binding__ in ("PySide", "PyQt4"):
            option = QStyleOptionViewItemV4(option)

        painter.save()

        item_rect = QtCore.QRect(option.rect)
        item_rect.setHeight(option.rect.height() - self.bar_height)

        subset_colors = index.data(ASSET_UNDERLINE_COLORS_ROLE) or []
        subset_colors_width = 0
        if subset_colors:
            subset_colors_width = option.rect.width() / len(subset_colors)

        subset_rects = []
        counter = 0
        for subset_c in subset_colors:
            new_color = None
            new_rect = None
            if subset_c:
                new_color = QtGui.QColor(*subset_c)

                new_rect = QtCore.QRect(
                    option.rect.left() + (counter * subset_colors_width),
                    option.rect.top() + (
                        option.rect.height() - self.bar_height
                    ),
                    subset_colors_width,
                    self.bar_height
                )
            subset_rects.append((new_color, new_rect))
            counter += 1

        # Background
        if option.state & QtWidgets.QStyle.State_Selected:
            if len(subset_colors) == 0:
                item_rect.setTop(item_rect.top() + (self.bar_height / 2))

            if option.state & QtWidgets.QStyle.State_MouseOver:
                bg_color = self._selected_hover_color
            else:
                bg_color = self._selected_color
        else:
            item_rect.setTop(item_rect.top() + (self.bar_height / 2))
            if option.state & QtWidgets.QStyle.State_MouseOver:
                bg_color = self._hover_color
            else:
                bg_color = QtGui.QColor()
                bg_color.setAlpha(0)

        # When not needed to do a rounded corners (easier and without
        #   painter restore):
        # painter.fillRect(
        #     item_rect,
        #     QtGui.QBrush(bg_color)
        # )
        pen = painter.pen()
        pen.setStyle(QtCore.Qt.NoPen)
        pen.setWidth(0)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(bg_color))
        painter.drawRoundedRect(option.rect, 3, 3)

        if option.state & QtWidgets.QStyle.State_Selected:
            for color, subset_rect in subset_rects:
                if not color or not subset_rect:
                    continue
                painter.fillRect(subset_rect, QtGui.QBrush(color))

        painter.restore()
        painter.save()

        # Icon
        icon_index = index.model().index(
            index.row(), index.column(), index.parent()
        )
        # - Default icon_rect if not icon
        icon_rect = QtCore.QRect(
            item_rect.left(),
            item_rect.top(),
            # To make sure it's same size all the time
            option.rect.height() - self.bar_height,
            option.rect.height() - self.bar_height
        )
        icon = index.model().data(icon_index, QtCore.Qt.DecorationRole)

        if icon:
            mode = QtGui.QIcon.Normal
            if not (option.state & QtWidgets.QStyle.State_Enabled):
                mode = QtGui.QIcon.Disabled
            elif option.state & QtWidgets.QStyle.State_Selected:
                mode = QtGui.QIcon.Selected

            if isinstance(icon, QtGui.QPixmap):
                icon = QtGui.QIcon(icon)
                option.decorationSize = icon.size() / icon.devicePixelRatio()

            elif isinstance(icon, QtGui.QColor):
                pixmap = QtGui.QPixmap(option.decorationSize)
                pixmap.fill(icon)
                icon = QtGui.QIcon(pixmap)

            elif isinstance(icon, QtGui.QImage):
                icon = QtGui.QIcon(QtGui.QPixmap.fromImage(icon))
                option.decorationSize = icon.size() / icon.devicePixelRatio()

            elif isinstance(icon, QtGui.QIcon):
                state = QtGui.QIcon.Off
                if option.state & QtWidgets.QStyle.State_Open:
                    state = QtGui.QIcon.On
                actual_size = option.icon.actualSize(
                    option.decorationSize, mode, state
                )
                option.decorationSize = QtCore.QSize(
                    min(option.decorationSize.width(), actual_size.width()),
                    min(option.decorationSize.height(), actual_size.height())
                )

            state = QtGui.QIcon.Off
            if option.state & QtWidgets.QStyle.State_Open:
                state = QtGui.QIcon.On

            icon.paint(
                painter, icon_rect,
                QtCore.Qt.AlignLeft, mode, state
            )

        # Text
        text_rect = QtCore.QRect(
            icon_rect.left() + icon_rect.width() + 2,
            item_rect.top(),
            item_rect.width(),
            item_rect.height()
        )

        painter.drawText(
            text_rect, QtCore.Qt.AlignVCenter,
            index.data(QtCore.Qt.DisplayRole)
        )

        painter.restore()


class AssetModel(QtGui.QStandardItemModel):
    """A model listing assets in the silo in the active project.

    The assets are displayed in a treeview, they are visually parented by
    a `visualParent` field in the database containing an `_id` to a parent
    asset.

    """

    _doc_fetched = QtCore.Signal()
    refreshed = QtCore.Signal(bool)

    # Asset document projection
    _asset_projection = {
        "type": 1,
        "schema": 1,
        "name": 1,
        "parent": 1,
        "data.visualParent": 1,
        "data.label": 1,
        "data.tags": 1,
        "data.icon": 1,
        "data.color": 1,
        "data.deprecated": 1
    }

    def __init__(self, dbcon, parent=None):
        super(AssetModel, self).__init__(parent=parent)
        self.dbcon = dbcon

        self._doc_fetching_thread = None
        self._doc_fetching_stop = False
        self._doc_payload = []

        self._doc_fetched.connect(self._on_docs_fetched)

        self._items_with_color_by_id = {}
        self._items_by_asset_id = {}

    def get_index_by_asset_id(self, asset_id):
        item = self._items_by_asset_id.get(asset_id)
        if item is not None:
            return item.index()
        return QtCore.QModelIndex()

    def get_indexes_by_asset_ids(self, asset_ids):
        return [
            self.get_index_by_asset_id(asset_id)
            for asset_id in asset_ids
        ]

    def get_index_by_asset_name(self, asset_name):
        indexes = self.get_indexes_by_asset_names([asset_name])
        for index in indexes:
            if index.isValid():
                return index
        return indexes[0]

    def get_indexes_by_asset_names(self, asset_names):
        asset_ids_by_name = {
            asset_name: None
            for asset_name in asset_names
        }

        for asset_id, item in self._items_by_asset_id.items():
            asset_name = item.data(ASSET_NAME_ROLE)
            if asset_name in asset_ids_by_name:
                asset_ids_by_name[asset_name] = asset_id

        asset_ids = [
            asset_ids_by_name[asset_name]
            for asset_name in asset_names
        ]

        return self.get_indexes_by_asset_ids(asset_ids)

    def refresh(self, force=False):
        """Refresh the data for the model."""
        # Skip fetch if there is already other thread fetching documents
        if self._doc_fetching_thread is not None:
            if not force:
                return
            self._stop_fetch_thread()

        # Fetch documents from mongo
        # Restart payload
        self._doc_payload = []
        self._doc_fetching_stop = False
        self._doc_fetching_thread = DynamicQThread(self._threaded_fetch)
        self._doc_fetching_thread.start()

    def clear_underlines(self):
        for asset_id in tuple(self._items_with_color_by_id.keys()):
            item = self._items_with_color_by_id.pop(asset_id)
            item.setData(None, ASSET_UNDERLINE_COLORS_ROLE)

    def set_underline_colors(self, colors_by_asset_id):
        self.clear_underlines()

        for asset_id, colors in colors_by_asset_id.items():
            item = self._items_by_asset_id.get(asset_id)
            if item is None:
                continue
            item.setData(colors, ASSET_UNDERLINE_COLORS_ROLE)

    def _on_docs_fetched(self):
        asset_docs = self._doc_payload

        asset_ids = set()
        asset_docs_by_id = {}
        asset_ids_by_parents = collections.defaultdict(set)
        for asset_doc in asset_docs:
            asset_id = asset_doc["_id"]
            asset_data = asset_doc.get("data") or {}
            parent_id = asset_data.get("visualParent")
            asset_ids.add(asset_id)
            asset_docs_by_id[asset_id] = asset_doc
            asset_ids_by_parents[parent_id].add(asset_id)

        root_item = self.invisibleRootItem()
        asset_items_queue = collections.deque()
        asset_items_queue.append((None, root_item))

        removed_asset_ids = set()
        while asset_items_queue:
            parent_id, parent_item = asset_items_queue.popleft()
            children_ids = asset_ids_by_parents[parent_id]
            if not children_ids:
                continue

            for row in reversed(range(parent_item.rowCount())):
                child_item = parent_item.child(row, 0)
                asset_id = child_item.data(ASSET_ID_ROLE)
                if asset_id not in children_ids:
                    parent_item.removeRow(row)
                    if asset_id not in asset_docs_by_id:
                        removed_asset_ids.add(asset_id)
                    continue

                children_ids.remove(asset_id)
                asset_items_queue.append((asset_id, child_item))

            new_items = []
            for asset_id in children_ids:
                item = QtGui.QStandardItem()
                item.setEditable(False)
                item.setData(asset_id, ASSET_ID_ROLE)
                new_items.append(item)
                self._items_by_asset_id[asset_id] = item
                asset_items_queue.append((asset_id, item))

            if new_items:
                parent_item.appendRows(new_items)

        for asset_id in removed_asset_ids:
            self._items_by_asset_id.pop(asset_id)
            if asset_id in self._items_with_color_by_id:
                self._items_with_color_by_id.pop(asset_id)

        # Refresh data
        for asset_id, item in self._items_by_asset_id.items():
            asset_doc = asset_docs_by_id[asset_id]

            asset_name = asset_doc["name"]
            if item.data(ASSET_NAME_ROLE) != asset_name:
                item.setData(asset_name, ASSET_NAME_ROLE)

            asset_data = asset_doc.get("data") or {}
            asset_label = asset_data.get("label") or asset_name
            if item.data(ASSET_LABEL_ROLE) != asset_label:
                item.setData(asset_label, QtCore.Qt.DisplayRole)
                item.setData(asset_label, ASSET_LABEL_ROLE)

            icon_color = asset_data.get("color") or style.colors.default
            icon_name = asset_data.get("icon")
            if not icon_name:
                # Use default icons if no custom one is specified.
                # If it has children show a full folder, otherwise
                # show an open folder
                if item.rowCount() > 0:
                    icon_name = "folder"
                else:
                    icon_name = "folder-o"

            try:
                # font-awesome key
                full_icon_name = "fa.{0}".format(icon_name)
                icon = qtawesome.icon(full_icon_name, color=icon_color)
                item.setData(icon, QtCore.Qt.DecorationRole)

            except Exception as exception:
                pass

        self.refreshed.emit(bool(self._items_by_asset_id))

        self._stop_fetch_thread()

    def _threaded_fetch(self):
        asset_docs = self._fetch_asset_docs() or []
        if self._doc_fetching_stop:
            return

        self._doc_payload = asset_docs

        # Emit doc fetched only if was not stopped
        self._doc_fetched.emit()

    def _fetch_asset_docs(self):
        if not self.dbcon.Session.get("AVALON_PROJECT"):
            return

        project_doc = self.dbcon.find_one(
            {"type": "project"},
            {"_id": True}
        )
        if not project_doc:
            return

        # Get all assets sorted by name
        return list(self.dbcon.find(
            {"type": "asset"},
            self._asset_projection
        ))

    def _stop_fetch_thread(self):
        if self._doc_fetching_thread is not None:
            self._doc_fetching_stop = True
            while self._doc_fetching_thread.isRunning():
                time.sleep(0.01)
            self._doc_fetching_thread = None
