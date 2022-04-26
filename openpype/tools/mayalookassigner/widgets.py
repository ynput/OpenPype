import logging
from collections import defaultdict

from Qt import QtWidgets, QtCore

from openpype.tools.utils.models import TreeModel
from openpype.tools.utils.lib import (
    preserve_expanded_rows,
    preserve_selection,
)

from .models import (
    AssetModel,
    LookModel
)
from . import commands
from .views import View

from maya import cmds


class AssetOutliner(QtWidgets.QWidget):
    refreshed = QtCore.Signal()
    selection_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super(AssetOutliner, self).__init__(parent)

        title = QtWidgets.QLabel("Assets", self)
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 12px")

        model = AssetModel()
        view = View(self)
        view.setModel(model)
        view.customContextMenuRequested.connect(self.right_mouse_menu)
        view.setSortingEnabled(False)
        view.setHeaderHidden(True)
        view.setIndentation(10)

        from_all_asset_btn = QtWidgets.QPushButton(
            "Get All Assets", self
        )
        from_selection_btn = QtWidgets.QPushButton(
            "Get Assets From Selection", self
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(from_all_asset_btn)
        layout.addWidget(from_selection_btn)
        layout.addWidget(view)

        # Build connections
        from_selection_btn.clicked.connect(self.get_selected_assets)
        from_all_asset_btn.clicked.connect(self.get_all_assets)

        selection_model = view.selectionModel()
        selection_model.selectionChanged.connect(self.selection_changed)

        self.view = view
        self.model = model

        self.log = logging.getLogger(__name__)

    def clear(self):
        self.model.clear()

        # fix looks remaining visible when no items present after "refresh"
        # todo: figure out why this workaround is needed.
        self.selection_changed.emit()

    def add_items(self, items):
        """Add new items to the outliner"""

        self.model.add_items(items)
        self.refreshed.emit()

    def get_selected_items(self):
        """Get current selected items from view

        Returns:
            list: list of dictionaries
        """

        selection_model = self.view.selectionModel()
        return [row.data(TreeModel.ItemRole)
                for row in selection_model.selectedRows(0)]

    def get_all_assets(self):
        """Add all items from the current scene"""

        items = []
        with preserve_expanded_rows(self.view):
            with preserve_selection(self.view):
                self.clear()
                nodes = commands.get_all_asset_nodes()
                items = commands.create_items_from_nodes(nodes)
                self.add_items(items)

        return len(items) > 0

    def get_selected_assets(self):
        """Add all selected items from the current scene"""

        with preserve_expanded_rows(self.view):
            with preserve_selection(self.view):
                self.clear()
                nodes = commands.get_selected_nodes()
                items = commands.create_items_from_nodes(nodes)
                self.add_items(items)

    def get_nodes(self, selection=False):
        """Find the nodes in the current scene per asset."""

        items = self.get_selected_items()

        # Collect all nodes by hash (optimization)
        if not selection:
            nodes = cmds.ls(dag=True, long=True)
        else:
            nodes = commands.get_selected_nodes()
        id_nodes = commands.create_asset_id_hash(nodes)

        # Collect the asset item entries per asset
        # and collect the namespaces we'd like to apply
        assets = {}
        asset_namespaces = defaultdict(set)
        for item in items:
            asset_id = str(item["asset"]["_id"])
            asset_name = item["asset"]["name"]
            asset_namespaces[asset_name].add(item.get("namespace"))

            if asset_name in assets:
                continue

            assets[asset_name] = item
            assets[asset_name]["nodes"] = id_nodes.get(asset_id, [])

        # Filter nodes to namespace (if only namespaces were selected)
        for asset_name in assets:
            namespaces = asset_namespaces[asset_name]

            # When None is present there should be no filtering
            if None in namespaces:
                continue

            # Else only namespaces are selected and *not* the top entry so
            # we should filter to only those namespaces.
            nodes = assets[asset_name]["nodes"]
            nodes = [node for node in nodes if
                     commands.get_namespace_from_node(node) in namespaces]
            assets[asset_name]["nodes"] = nodes

        return assets

    def select_asset_from_items(self):
        """Select nodes from listed asset"""

        items = self.get_nodes(selection=False)
        nodes = []
        for item in items.values():
            nodes.extend(item["nodes"])

        commands.select(nodes)

    def right_mouse_menu(self, pos):
        """Build RMB menu for asset outliner"""

        active = self.view.currentIndex()  # index under mouse
        active = active.sibling(active.row(), 0)  # get first column
        globalpos = self.view.viewport().mapToGlobal(pos)

        menu = QtWidgets.QMenu(self.view)

        # Direct assignment
        apply_action = QtWidgets.QAction(menu, text="Select nodes")
        apply_action.triggered.connect(self.select_asset_from_items)

        if not active.isValid():
            apply_action.setEnabled(False)

        menu.addAction(apply_action)

        menu.exec_(globalpos)


class LookOutliner(QtWidgets.QWidget):
    menu_apply_action = QtCore.Signal()

    def __init__(self, parent=None):
        super(LookOutliner, self).__init__(parent)

        # Looks from database
        title = QtWidgets.QLabel("Looks", self)
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 12px")
        title.setAlignment(QtCore.Qt.AlignCenter)

        model = LookModel()

        # Proxy for dynamic sorting
        proxy = QtCore.QSortFilterProxyModel()
        proxy.setSourceModel(model)

        view = View(self)
        view.setModel(proxy)
        view.setMinimumHeight(180)
        view.setToolTip("Use right mouse button menu for direct actions")
        view.customContextMenuRequested.connect(self.right_mouse_menu)
        view.sortByColumn(0, QtCore.Qt.AscendingOrder)

        # look manager layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(view)

        self.view = view
        self.model = model

    def clear(self):
        self.model.clear()

    def add_items(self, items):
        self.model.add_items(items)

    def get_selected_items(self):
        """Get current selected items from view

        Returns:
            list: list of dictionaries
        """

        items = [i.data(TreeModel.ItemRole) for i in self.view.get_indices()]
        return [item for item in items if item is not None]

    def right_mouse_menu(self, pos):
        """Build RMB menu for look view"""

        active = self.view.currentIndex()  # index under mouse
        active = active.sibling(active.row(), 0)  # get first column
        globalpos = self.view.viewport().mapToGlobal(pos)

        if not active.isValid():
            return

        menu = QtWidgets.QMenu(self.view)

        # Direct assignment
        apply_action = QtWidgets.QAction(menu, text="Assign looks..")
        apply_action.triggered.connect(self.menu_apply_action)

        menu.addAction(apply_action)

        menu.exec_(globalpos)
