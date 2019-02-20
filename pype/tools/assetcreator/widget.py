import logging
import contextlib

from avalon.vendor import qtawesome as awesome
from avalon.vendor.Qt import QtWidgets, QtCore, QtGui
from avalon import io, schema
from avalon import style

from .model import (
    TreeModel,
    Node,
    RecursiveSortFilterProxyModel,
    DeselectableTreeView
)

log = logging.getLogger(__name__)


def _iter_model_rows(model,
                     column,
                     include_root=False):
    """Iterate over all row indices in a model"""
    indices = [QtCore.QModelIndex()]  # start iteration at root

    for index in indices:

        # Add children to the iterations
        child_rows = model.rowCount(index)
        for child_row in range(child_rows):
            child_index = model.index(child_row, column, index)
            indices.append(child_index)

        if not include_root and not index.isValid():
            continue

        yield index


@contextlib.contextmanager
def preserve_expanded_rows(tree_view,
                           column=0,
                           role=QtCore.Qt.DisplayRole):
    """Preserves expanded row in QTreeView by column's data role.

    This function is created to maintain the expand vs collapse status of
    the model items. When refresh is triggered the items which are expanded
    will stay expanded and vise versa.

    Arguments:
        tree_view (QWidgets.QTreeView): the tree view which is
            nested in the application
        column (int): the column to retrieve the data from
        role (int): the role which dictates what will be returned

    Returns:
        None

    """

    model = tree_view.model()

    expanded = set()

    for index in _iter_model_rows(model,
                                  column=column,
                                  include_root=False):
        if tree_view.isExpanded(index):
            value = index.data(role)
            expanded.add(value)

    try:
        yield
    finally:
        if not expanded:
            return

        for index in _iter_model_rows(model,
                                      column=column,
                                      include_root=False):
            value = index.data(role)
            state = value in expanded
            if state:
                tree_view.expand(index)
            else:
                tree_view.collapse(index)


@contextlib.contextmanager
def preserve_selection(tree_view,
                       column=0,
                       role=QtCore.Qt.DisplayRole,
                       current_index=True):
    """Preserves row selection in QTreeView by column's data role.

    This function is created to maintain the selection status of
    the model items. When refresh is triggered the items which are expanded
    will stay expanded and vise versa.

        tree_view (QWidgets.QTreeView): the tree view nested in the application
        column (int): the column to retrieve the data from
        role (int): the role which dictates what will be returned

    Returns:
        None

    """

    model = tree_view.model()
    selection_model = tree_view.selectionModel()
    flags = selection_model.Select | selection_model.Rows

    if current_index:
        current_index_value = tree_view.currentIndex().data(role)
    else:
        current_index_value = None

    selected_rows = selection_model.selectedRows()
    if not selected_rows:
        yield
        return

    selected = set(row.data(role) for row in selected_rows)
    try:
        yield
    finally:
        if not selected:
            return

        # Go through all indices, select the ones with similar data
        for index in _iter_model_rows(model,
                                      column=column,
                                      include_root=False):

            value = index.data(role)
            state = value in selected
            if state:
                tree_view.scrollTo(index)  # Ensure item is visible
                selection_model.select(index, flags)

            if current_index_value and value == current_index_value:
                tree_view.setCurrentIndex(index)


def _list_project_silos():
    """List the silos from the project's configuration"""
    # old way: silos = io.distinct("silo")
    # new, Backwards compatible way to get all silos from DB:
    silos = [s['name'] for s in io.find({"type": "asset", "silo": None})]
    silos_old = io.distinct("silo")
    for silo in silos_old:
        if silo not in silos and silo is not None:
            silos.append(silo)

    if not silos:
        project = io.find_one({"type": "project"})
        log.warning("Project '%s' has no active silos", project['name'])

    return list(sorted(silos))


class AssetModel(TreeModel):
    """A model listing assets in the silo in the active project.

    The assets are displayed in a treeview, they are visually parented by
    a `visualParent` field in the database containing an `_id` to a parent
    asset.

    """

    COLUMNS = ["label"]
    Name = 0
    Deprecated = 2
    ObjectId = 3

    DocumentRole = QtCore.Qt.UserRole + 2
    ObjectIdRole = QtCore.Qt.UserRole + 3

    def __init__(self, parent=None):
        super(AssetModel, self).__init__(parent=parent)
        self.refresh()

    def _add_hierarchy(self, parent=None):

        # Find the assets under the parent
        find_data = {
            "type": "asset"
        }
        if parent is None:
            find_data['$or'] = [
                {'data.visualParent': {'$exists': False}},
                {'data.visualParent': None}
            ]
        else:
            find_data["data.visualParent"] = parent['_id']

        assets = io.find(find_data).sort('name', 1)
        for asset in assets:
            # get label from data, otherwise use name
            data = asset.get("data", {})
            label = data.get("label", asset['name'])
            tags = data.get("tags", [])

            # store for the asset for optimization
            deprecated = "deprecated" in tags

            node = Node({
                "_id": asset['_id'],
                "name": asset["name"],
                "label": label,
                "type": asset['type'],
                "tags": ", ".join(tags),
                "deprecated": deprecated,
                "_document": asset
            })
            self.add_child(node, parent=parent)

            # Add asset's children recursively
            self._add_hierarchy(node)

    def refresh(self):
        """Refresh the data for the model."""

        self.clear()
        self.beginResetModel()
        self._add_hierarchy(parent=None)
        self.endResetModel()

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):

        if not index.isValid():
            return

        node = index.internalPointer()
        if role == QtCore.Qt.DecorationRole:        # icon

            column = index.column()
            if column == self.Name:

                # Allow a custom icon and custom icon color to be defined
                data = node["_document"]["data"]
                icon = data.get("icon", None)
                color = data.get("color", style.colors.default)

                if icon is None:
                    # Use default icons if no custom one is specified.
                    # If it has children show a full folder, otherwise
                    # show an open folder
                    has_children = self.rowCount(index) > 0
                    icon = "folder" if has_children else "folder-o"

                # Make the color darker when the asset is deprecated
                if node.get("deprecated", False):
                    color = QtGui.QColor(color).darker(250)

                try:
                    key = "fa.{0}".format(icon)  # font-awesome key
                    icon = awesome.icon(key, color=color)
                    return icon
                except Exception as exception:
                    # Log an error message instead of erroring out completely
                    # when the icon couldn't be created (e.g. invalid name)
                    log.error(exception)

                return

        if role == QtCore.Qt.ForegroundRole:        # font color
            if "deprecated" in node.get("tags", []):
                return QtGui.QColor(style.colors.light).darker(250)

        if role == self.ObjectIdRole:
            return node.get("_id", None)

        if role == self.DocumentRole:
            return node.get("_document", None)

        return super(AssetModel, self).data(index, role)


class AssetView(DeselectableTreeView):
    """Item view.

    This implements a context menu.

    """

    def __init__(self):
        super(AssetView, self).__init__()
        self.setIndentation(15)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setHeaderHidden(True)


class SiloTabWidget(QtWidgets.QTabBar):
    """Silo widget

    Allows to add a silo, with "+" tab.

    Note:
        When no silos are present an empty stub silo is added to
        use as the "blank" tab to start on, so the + tab becomes
        clickable.

    """

    silo_changed = QtCore.Signal(str)
    silo_added = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(SiloTabWidget, self).__init__(parent=parent)
        self._previous_tab_index = -1
        self.set_silos([])

        self.setContentsMargins(0, 0, 0, 0)
        self.setFixedHeight(28)
        font = QtGui.QFont()
        font.setBold(True)
        self.setFont(font)

        self.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):

        if index == self._previous_tab_index:
            return

        # If it's the last tab
        num = self.count()
        if index == num - 1:
            self.on_add_silo()
            self.setCurrentIndex(self._previous_tab_index)
            return

        silo = self.tabText(index)
        self.silo_changed.emit(silo)

        # Store for the next calls
        self._previous_tab_index = index

    def clear(self):
        """Removes all tabs.

        Implemented similar to `QTabWidget.clear()`

        """
        for i in range(self.count()):
            self.removeTab(0)

    def set_silos(self, silos):

        current_silo = self.get_current_silo()

        if not silos:
            # Add an emtpy stub tab to start on.
            silos = [""]

        # Populate the silos without emitting signals
        self.blockSignals(True)
        self.clear()
        for silo in sorted(silos):
            self.addTab(silo)

        # Add the "+" tab
        self.addTab("+")

        self.set_current_silo(current_silo)
        self.blockSignals(False)

        # Assume the current index is "fine"
        self._previous_tab_index = self.currentIndex()

        # Only emit a silo changed signal if the new signal
        # after refresh is not the same as prior to it (e.g.
        # when the silo was removed, or alike.)
        if current_silo != self.get_current_silo():
            self.currentChanged.emit(self.currentIndex())

    def set_current_silo(self, silo):
        """Set the active silo by name or index.

        Args:
            silo (str or int): The silo name or index.
            emit (bool): Whether to emit the change signals

        """

        # Already set
        if silo == self.get_current_silo():
            return

        # Otherwise change the silo box to the name
        for i in range(self.count()):
            text = self.tabText(i)
            if text == silo:
                self.setCurrentIndex(i)
                break

    def get_current_silo(self):
        index = self.currentIndex()
        return self.tabText(index)

    def on_add_silo(self):
        silo, state = QtWidgets.QInputDialog.getText(self,
                                                     "Silo name",
                                                     "Create new silo:")
        if not state or not silo:
            return

        self.add_silo(silo)

    def get_silos(self):
        """Return the currently available silos"""

        # Ignore first tab if empty
        # Ignore the last tab because it is the "+" tab
        silos = []
        for i in range(self.count() - 1):
            label = self.tabText(i)
            if i == 0 and not label:
                continue
            silos.append(label)
        return silos

    def add_silo(self, silo):

        # Add the silo to tab
        silos = self.get_silos()
        silos.append(silo)
        silos = list(set(silos))  # ensure unique
        self.set_silos(silos)
        self.silo_added.emit(silo)

        self.set_current_silo(silo)


class AssetWidget(QtWidgets.QWidget):
    """A Widget to display a tree of assets with filter

    To list the assets of the active project:
        >>> # widget = AssetWidget()
        >>> # widget.refresh()
        >>> # widget.show()

    """

    silo_changed = QtCore.Signal(str)    # on silo combobox change
    assets_refreshed = QtCore.Signal()   # on model refresh
    selection_changed = QtCore.Signal()  # on view selection change
    current_changed = QtCore.Signal()    # on view current index change

    def __init__(self, parent=None):
        super(AssetWidget, self).__init__(parent=parent)
        self.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Tree View
        model = AssetModel()
        proxy = RecursiveSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        view = AssetView()
        view.setModel(proxy)

        # Header
        header = QtWidgets.QHBoxLayout()

        icon = awesome.icon("fa.refresh", color=style.colors.light)
        refresh = QtWidgets.QPushButton(icon, "")
        refresh.setToolTip("Refresh items")

        filter = QtWidgets.QLineEdit()
        filter.textChanged.connect(proxy.setFilterFixedString)
        filter.setPlaceholderText("Filter assets..")

        header.addWidget(filter)
        header.addWidget(refresh)

        # Layout
        layout.addLayout(header)
        layout.addWidget(view)

        # Signals/Slots
        selection = view.selectionModel()
        selection.selectionChanged.connect(self.selection_changed)
        selection.currentChanged.connect(self.current_changed)
        # silo.silo_changed.connect(self._on_silo_changed)
        refresh.clicked.connect(self.refresh)

        self.refreshButton = refresh
        # self.silo = silo
        self.model = model
        self.proxy = proxy
        self.view = view

    # def _on_silo_changed(self):
    #     """Callback for silo change"""
    #
    #     self._refresh_model()
    #     silo = self.get_current_silo()
    #     self.silo_changed.emit(silo)
    #     self.selection_changed.emit()

    def _refresh_model(self):

        # silo = self.get_current_silo()
        # with preserve_expanded_rows(self.view,
        #                             column=0,
        #                             role=self.model.ObjectIdRole):
        #     with preserve_selection(self.view,
        #                             column=0,
        #                             role=self.model.ObjectIdRole):
        #         self.model.set_silo(silo)

        self.assets_refreshed.emit()

    def refresh(self):

        # silos = _list_project_silos()
        # self.silo.set_silos(silos)
        # set first silo as active so tasks are shown
        # if len(silos) > 0:
        #     self.silo.set_current_silo(self.silo.tabText(0))
        self._refresh_model()

    # def get_current_silo(self):
    #     """Returns the currently active silo."""
    #     return self.silo.get_current_silo()

    # def get_silo_object(self, silo_name=None):
    #     """ Returns silo object from db. None if not found.
    #     Current silo is found if silo_name not entered."""
    #     if silo_name is None:
    #         silo_name = self.get_current_silo()
    #     try:
    #         return io.find_one({"type": "asset", "name": silo_name})
    #     except Exception:
    #         return None

    def get_active_asset(self):
        """Return the asset id the current asset."""
        current = self.view.currentIndex()
        return current.data(self.model.ObjectIdRole)

    def get_active_index(self):
        return self.view.currentIndex()

    def get_selected_assets(self):
        """Return the assets' ids that are selected."""
        selection = self.view.selectionModel()
        rows = selection.selectedRows()
        return [row.data(self.model.ObjectIdRole) for row in rows]

    # def set_silo(self, silo):
    #     """Set the active silo tab"""
    #     self.silo.set_current_silo(silo)

    def select_assets(self, assets, expand=True):
        """Select assets by name.

        Args:
            assets (list): List of asset names
            expand (bool): Whether to also expand to the asset in the view

        Returns:
            None

        """
        # TODO: Instead of individual selection optimize for many assets

        assert isinstance(assets,
                          (tuple, list)), "Assets must be list or tuple"

        # Clear selection
        selection_model = self.view.selectionModel()
        selection_model.clearSelection()

        # Select
        mode = selection_model.Select | selection_model.Rows
        for index in _iter_model_rows(self.proxy,
                                      column=0,
                                      include_root=False):
            data = index.data(self.model.NodeRole)
            name = data['name']
            if name in assets:
                selection_model.select(index, mode)

                if expand:
                    self.view.expand(index)

                # Set the currently active index
                self.view.setCurrentIndex(index)
