import collections

from Qt import QtWidgets, QtCore, QtGui
from openpype.tools.utils import (
    PlaceholderLineEdit,
    RecursiveSortFilterProxyModel,
    get_asset_icon,
)
from openpype.tools.utils.assets_widget import (
    SingleSelectAssetsWidget,
    ASSET_ID_ROLE,
    ASSET_NAME_ROLE
)


class CreateDialogAssetsWidget(SingleSelectAssetsWidget):
    current_context_required = QtCore.Signal()
    header_height_changed = QtCore.Signal(int)

    def __init__(self, controller, parent):
        self._controller = controller
        super(CreateDialogAssetsWidget, self).__init__(None, parent)

        self.set_refresh_btn_visibility(False)
        self.set_current_asset_btn_visibility(False)

        self._current_asset_name = None
        self._last_selection = None
        self._enabled = None

        self._last_filter_height = None

    def _check_header_height(self):
        """Catch header height changes.

        Label on top of creaters should have same height so Creators view has
        same offset.
        """
        height = self.header_widget.height()
        if height != self._last_filter_height:
            self._last_filter_height = height
            self.header_height_changed.emit(height)

    def resizeEvent(self, event):
        super(CreateDialogAssetsWidget, self).resizeEvent(event)
        self._check_header_height()

    def showEvent(self, event):
        super(CreateDialogAssetsWidget, self).showEvent(event)
        self._check_header_height()

    def _on_current_asset_click(self):
        self.current_context_required.emit()

    def set_enabled(self, enabled):
        if self._enabled == enabled:
            return
        self._enabled = enabled
        if not enabled:
            self._last_selection = self.get_selected_asset_id()
            self._clear_selection()
        elif self._last_selection is not None:
            self.select_asset(self._last_selection)

    def _select_indexes(self, *args, **kwargs):
        super(CreateDialogAssetsWidget, self)._select_indexes(*args, **kwargs)
        if self._enabled:
            return
        self._last_selection = self.get_selected_asset_id()
        self._clear_selection()

    def set_current_asset_name(self, asset_name):
        self._current_asset_name = asset_name
        # Hide set current asset if there is no one
        self.set_current_asset_btn_visibility(asset_name is not None)

    def _get_current_session_asset(self):
        return self._current_asset_name

    def _create_source_model(self):
        return AssetsHierarchyModel(self._controller)

    def _refresh_model(self):
        self._model.reset()
        self._on_model_refresh(self._model.rowCount() > 0)


class AssetsHierarchyModel(QtGui.QStandardItemModel):
    """Assets hiearrchy model.

    For selecting asset for which should beinstance created.

    Uses controller to load asset hierarchy. All asset documents are stored by
    their parents.
    """

    def __init__(self, controller):
        super(AssetsHierarchyModel, self).__init__()
        self._controller = controller

        self._items_by_name = {}
        self._items_by_asset_id = {}

    def reset(self):
        self.clear()

        self._items_by_name = {}
        self._items_by_asset_id = {}
        assets_by_parent_id = self._controller.get_asset_hierarchy()

        items_by_name = {}
        items_by_asset_id = {}
        _queue = collections.deque()
        _queue.append((self.invisibleRootItem(), None))
        while _queue:
            parent_item, parent_id = _queue.popleft()
            children = assets_by_parent_id.get(parent_id)
            if not children:
                continue

            children_by_name = {
                child["name"]: child
                for child in children
            }
            items = []
            for name in sorted(children_by_name.keys()):
                child = children_by_name[name]
                child_id = child["_id"]
                has_children = bool(assets_by_parent_id.get(child_id))
                icon = get_asset_icon(child, has_children)

                item = QtGui.QStandardItem(name)
                item.setFlags(
                    QtCore.Qt.ItemIsEnabled
                    | QtCore.Qt.ItemIsSelectable
                )
                item.setData(icon, QtCore.Qt.DecorationRole)
                item.setData(child_id, ASSET_ID_ROLE)
                item.setData(name, ASSET_NAME_ROLE)

                items_by_name[name] = item
                items_by_asset_id[child_id] = item
                items.append(item)
                _queue.append((item, child_id))

            parent_item.appendRows(items)

        self._items_by_name = items_by_name
        self._items_by_asset_id = items_by_asset_id

    def get_index_by_asset_id(self, asset_id):
        item = self._items_by_asset_id.get(asset_id)
        if item is not None:
            return item.index()
        return QtCore.QModelIndex()

    def get_index_by_asset_name(self, asset_name):
        item = self._items_by_name.get(asset_name)
        if item is None:
            return QtCore.QModelIndex()
        return item.index()

    def name_is_valid(self, item_name):
        return item_name in self._items_by_name


class AssetsDialog(QtWidgets.QDialog):
    """Dialog to select asset for a context of instance."""

    def __init__(self, controller, parent):
        super(AssetsDialog, self).__init__(parent)
        self.setWindowTitle("Select asset")

        model = AssetsHierarchyModel(controller)
        proxy_model = RecursiveSortFilterProxyModel()
        proxy_model.setSourceModel(model)
        proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        filter_input = PlaceholderLineEdit(self)
        filter_input.setPlaceholderText("Filter assets..")

        asset_view = QtWidgets.QTreeView(self)
        asset_view.setModel(proxy_model)
        asset_view.setHeaderHidden(True)
        asset_view.setFrameShape(QtWidgets.QFrame.NoFrame)
        asset_view.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)
        asset_view.setAlternatingRowColors(True)
        asset_view.setSelectionBehavior(QtWidgets.QTreeView.SelectRows)
        asset_view.setAllColumnsShowFocus(True)

        ok_btn = QtWidgets.QPushButton("OK", self)
        cancel_btn = QtWidgets.QPushButton("Cancel", self)

        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addStretch(1)
        btns_layout.addWidget(ok_btn)
        btns_layout.addWidget(cancel_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(filter_input, 0)
        layout.addWidget(asset_view, 1)
        layout.addLayout(btns_layout, 0)

        filter_input.textChanged.connect(self._on_filter_change)
        ok_btn.clicked.connect(self._on_ok_clicked)
        cancel_btn.clicked.connect(self._on_cancel_clicked)

        self._filter_input = filter_input
        self._ok_btn = ok_btn
        self._cancel_btn = cancel_btn

        self._model = model
        self._proxy_model = proxy_model

        self._asset_view = asset_view

        self._selected_asset = None
        # Soft refresh is enabled
        # - reset will happen at all cost if soft reset is enabled
        # - adds ability to call reset on multiple places without repeating
        self._soft_reset_enabled = True

        self._first_show = True
        self._default_height = 500

    def _on_first_show(self):
        center = self.rect().center()
        size = self.size()
        size.setHeight(self._default_height)

        self.resize(size)
        new_pos = self.mapToGlobal(center)
        new_pos.setX(new_pos.x() - int(self.width() / 2))
        new_pos.setY(new_pos.y() - int(self.height() / 2))
        self.move(new_pos)

    def showEvent(self, event):
        """Refresh asset model on show."""
        super(AssetsDialog, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self._on_first_show()
        # Refresh on show
        self.reset(False)

    def reset(self, force=True):
        """Reset asset model."""
        if not force and not self._soft_reset_enabled:
            return

        if self._soft_reset_enabled:
            self._soft_reset_enabled = False

        self._model.reset()

    def name_is_valid(self, name):
        """Is asset name valid.

        Args:
            name(str): Asset name that should be checked.
        """
        # Make sure we're reset
        self.reset(False)
        # Valid the name by model
        return self._model.name_is_valid(name)

    def _on_filter_change(self, text):
        """Trigger change of filter of assets."""
        self._proxy_model.setFilterFixedString(text)

    def _on_cancel_clicked(self):
        self.done(0)

    def _on_ok_clicked(self):
        index = self._asset_view.currentIndex()
        asset_name = None
        if index.isValid():
            asset_name = index.data(QtCore.Qt.DisplayRole)
        self._selected_asset = asset_name
        self.done(1)

    def set_selected_assets(self, asset_names):
        """Change preselected asset before showing the dialog.

        This also resets model and clean filter.
        """
        self.reset(False)
        self._asset_view.collapseAll()
        self._filter_input.setText("")

        indexes = []
        for asset_name in asset_names:
            index = self._model.get_index_by_asset_name(asset_name)
            if index.isValid():
                indexes.append(index)

        if not indexes:
            return

        index_deque = collections.deque()
        for index in indexes:
            index_deque.append(index)

        all_indexes = []
        while index_deque:
            index = index_deque.popleft()
            all_indexes.append(index)

            parent_index = index.parent()
            if parent_index.isValid():
                index_deque.append(parent_index)

        for index in all_indexes:
            proxy_index = self._proxy_model.mapFromSource(index)
            self._asset_view.expand(proxy_index)

    def get_selected_asset(self):
        """Get selected asset name."""
        return self._selected_asset
