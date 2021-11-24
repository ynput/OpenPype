import re
import time
import logging
import collections

import Qt
from Qt import QtCore, QtGui
from avalon.vendor import qtawesome
from avalon import style, io
from . import lib
from .constants import (
    PROJECT_IS_ACTIVE_ROLE,
    PROJECT_NAME_ROLE,
    DEFAULT_PROJECT_LABEL,
    TASK_ORDER_ROLE,
    TASK_TYPE_ROLE,
    TASK_NAME_ROLE
)

log = logging.getLogger(__name__)


class TreeModel(QtCore.QAbstractItemModel):

    Columns = list()
    ItemRole = QtCore.Qt.UserRole + 1
    item_class = None

    def __init__(self, parent=None):
        super(TreeModel, self).__init__(parent)
        self._root_item = self.ItemClass()

    @property
    def ItemClass(self):
        if self.item_class is not None:
            return self.item_class
        return Item

    def rowCount(self, parent=None):
        if parent is None or not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()
        return parent_item.childCount()

    def columnCount(self, parent):
        return len(self.Columns)

    def data(self, index, role):
        if not index.isValid():
            return None

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            item = index.internalPointer()
            column = index.column()

            key = self.Columns[column]
            return item.get(key, None)

        if role == self.ItemRole:
            return index.internalPointer()

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """Change the data on the items.

        Returns:
            bool: Whether the edit was successful
        """

        if index.isValid():
            if role == QtCore.Qt.EditRole:

                item = index.internalPointer()
                column = index.column()
                key = self.Columns[column]
                item[key] = value

                # passing `list()` for PyQt5 (see PYSIDE-462)
                if Qt.__binding__ in ("PyQt4", "PySide"):
                    self.dataChanged.emit(index, index)
                else:
                    self.dataChanged.emit(index, index, [role])

                # must return true if successful
                return True

        return False

    def setColumns(self, keys):
        assert isinstance(keys, (list, tuple))
        self.Columns = keys

    def headerData(self, section, orientation, role):

        if role == QtCore.Qt.DisplayRole:
            if section < len(self.Columns):
                return self.Columns[section]

        super(TreeModel, self).headerData(section, orientation, role)

    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled

        item = index.internalPointer()
        if item.get("enabled", True):
            flags |= QtCore.Qt.ItemIsSelectable

        return flags

    def parent(self, index):

        item = index.internalPointer()
        parent_item = item.parent()

        # If it has no parents we return invalid
        if parent_item == self._root_item or not parent_item:
            return QtCore.QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def index(self, row, column, parent=None):
        """Return index for row/column under parent"""

        if parent is None or not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()

        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        else:
            return QtCore.QModelIndex()

    def add_child(self, item, parent=None):
        if parent is None:
            parent = self._root_item

        parent.add_child(item)

    def column_name(self, column):
        """Return column key by index"""

        if column < len(self.Columns):
            return self.Columns[column]

    def clear(self):
        self.beginResetModel()
        self._root_item = self.ItemClass()
        self.endResetModel()


class Item(dict):
    """An item that can be represented in a tree view using `TreeModel`.

    The item can store data just like a regular dictionary.

    >>> data = {"name": "John", "score": 10}
    >>> item = Item(data)
    >>> assert item["name"] == "John"

    """

    def __init__(self, data=None):
        super(Item, self).__init__()

        self._children = list()
        self._parent = None

        if data is not None:
            assert isinstance(data, dict)
            self.update(data)

    def childCount(self):
        return len(self._children)

    def child(self, row):

        if row >= len(self._children):
            log.warning("Invalid row as child: {0}".format(row))
            return

        return self._children[row]

    def children(self):
        return self._children

    def parent(self):
        return self._parent

    def row(self):
        """
        Returns:
             int: Index of this item under parent"""
        if self._parent is not None:
            siblings = self.parent().children()
            return siblings.index(self)
        return -1

    def add_child(self, child):
        """Add a child to this item"""
        child._parent = self
        self._children.append(child)


class AssetModel(TreeModel):
    """A model listing assets in the silo in the active project.

    The assets are displayed in a treeview, they are visually parented by
    a `visualParent` field in the database containing an `_id` to a parent
    asset.

    """

    Columns = ["label"]
    Name = 0
    Deprecated = 2
    ObjectId = 3

    DocumentRole = QtCore.Qt.UserRole + 2
    ObjectIdRole = QtCore.Qt.UserRole + 3
    subsetColorsRole = QtCore.Qt.UserRole + 4

    doc_fetched = QtCore.Signal(bool)
    refreshed = QtCore.Signal(bool)

    # Asset document projection
    asset_projection = {
        "type": 1,
        "schema": 1,
        "name": 1,
        "silo": 1,
        "data.visualParent": 1,
        "data.label": 1,
        "data.tags": 1,
        "data.icon": 1,
        "data.color": 1,
        "data.deprecated": 1
    }

    def __init__(self, dbcon=None, parent=None, asset_projection=None):
        super(AssetModel, self).__init__(parent=parent)
        if dbcon is None:
            dbcon = io
        self.dbcon = dbcon
        self.asset_colors = {}

        # Projections for Mongo queries
        # - let ability to modify them if used in tools that require more than
        #   defaults
        if asset_projection:
            self.asset_projection = asset_projection

        self.asset_projection = asset_projection

        self._doc_fetching_thread = None
        self._doc_fetching_stop = False
        self._doc_payload = {}

        self.doc_fetched.connect(self.on_doc_fetched)

        self.refresh()

    def _add_hierarchy(self, assets, parent=None, silos=None):
        """Add the assets that are related to the parent as children items.

        This method does *not* query the database. These instead are queried
        in a single batch upfront as an optimization to reduce database
        queries. Resulting in up to 10x speed increase.

        Args:
            assets (dict): All assets in the currently active silo stored
                by key/value

        Returns:
            None

        """
        # Reset colors
        self.asset_colors = {}

        if silos:
            # WARNING: Silo item "_id" is set to silo value
            # mainly because GUI issue with perserve selection and expanded row
            # and because of easier hierarchy parenting (in "assets")
            for silo in silos:
                item = Item({
                    "_id": silo,
                    "name": silo,
                    "label": silo,
                    "type": "silo"
                })
                self.add_child(item, parent=parent)
                self._add_hierarchy(assets, parent=item)

        parent_id = parent["_id"] if parent else None
        current_assets = assets.get(parent_id, list())

        for asset in current_assets:
            # get label from data, otherwise use name
            data = asset.get("data", {})
            label = data.get("label", asset["name"])
            tags = data.get("tags", [])

            # store for the asset for optimization
            deprecated = "deprecated" in tags

            item = Item({
                "_id": asset["_id"],
                "name": asset["name"],
                "label": label,
                "type": asset["type"],
                "tags": ", ".join(tags),
                "deprecated": deprecated,
                "_document": asset
            })
            self.add_child(item, parent=parent)

            # Add asset's children recursively if it has children
            if asset["_id"] in assets:
                self._add_hierarchy(assets, parent=item)

            self.asset_colors[asset["_id"]] = []

    def on_doc_fetched(self, was_stopped):
        if was_stopped:
            self.stop_fetch_thread()
            return

        self.beginResetModel()

        assets_by_parent = self._doc_payload.get("assets_by_parent")
        silos = self._doc_payload.get("silos")
        if assets_by_parent is not None:
            # Build the hierarchical tree items recursively
            self._add_hierarchy(
                assets_by_parent,
                parent=None,
                silos=silos
            )

        self.endResetModel()

        has_content = bool(assets_by_parent) or bool(silos)
        self.refreshed.emit(has_content)

        self.stop_fetch_thread()

    def fetch(self):
        self._doc_payload = self._fetch() or {}
        # Emit doc fetched only if was not stopped
        self.doc_fetched.emit(self._doc_fetching_stop)

    def _fetch(self):
        if not self.dbcon.Session.get("AVALON_PROJECT"):
            return

        project_doc = self.dbcon.find_one(
            {"type": "project"},
            {"_id": True}
        )
        if not project_doc:
            return

        # Get all assets sorted by name
        db_assets = self.dbcon.find(
            {"type": "asset"},
            self.asset_projection
        ).sort("name", 1)

        # Group the assets by their visual parent's id
        assets_by_parent = collections.defaultdict(list)
        for asset in db_assets:
            if self._doc_fetching_stop:
                return
            parent_id = asset.get("data", {}).get("visualParent")
            assets_by_parent[parent_id].append(asset)

        return {
            "assets_by_parent": assets_by_parent,
            "silos": None
        }

    def stop_fetch_thread(self):
        if self._doc_fetching_thread is not None:
            self._doc_fetching_stop = True
            while self._doc_fetching_thread.isRunning():
                time.sleep(0.001)
            self._doc_fetching_thread = None

    def refresh(self, force=False):
        """Refresh the data for the model."""
        # Skip fetch if there is already other thread fetching documents
        if self._doc_fetching_thread is not None:
            if not force:
                return
            self.stop_fetch_thread()

        # Clear model items
        self.clear()

        # Fetch documents from mongo
        # Restart payload
        self._doc_payload = {}
        self._doc_fetching_stop = False
        self._doc_fetching_thread = lib.create_qthread(self.fetch)
        self._doc_fetching_thread.start()

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return False

        if role == self.subsetColorsRole:
            asset_id = index.data(self.ObjectIdRole)
            self.asset_colors[asset_id] = value

            if Qt.__binding__ in ("PyQt4", "PySide"):
                self.dataChanged.emit(index, index)
            else:
                self.dataChanged.emit(index, index, [role])

            return True

        return super(AssetModel, self).setData(index, value, role)

    def data(self, index, role):
        if not index.isValid():
            return

        item = index.internalPointer()
        if role == QtCore.Qt.DecorationRole:
            column = index.column()
            if column == self.Name:
                # Allow a custom icon and custom icon color to be defined
                data = item.get("_document", {}).get("data", {})
                icon = data.get("icon", None)
                if icon is None and item.get("type") == "silo":
                    icon = "database"
                color = data.get("color", style.colors.default)

                if icon is None:
                    # Use default icons if no custom one is specified.
                    # If it has children show a full folder, otherwise
                    # show an open folder
                    has_children = self.rowCount(index) > 0
                    icon = "folder" if has_children else "folder-o"

                # Make the color darker when the asset is deprecated
                if item.get("deprecated", False):
                    color = QtGui.QColor(color).darker(250)

                try:
                    key = "fa.{0}".format(icon)  # font-awesome key
                    icon = qtawesome.icon(key, color=color)
                    return icon
                except Exception as exception:
                    # Log an error message instead of erroring out completely
                    # when the icon couldn't be created (e.g. invalid name)
                    log.error(exception)

                return

        if role == QtCore.Qt.ForegroundRole:        # font color
            if "deprecated" in item.get("tags", []):
                return QtGui.QColor(style.colors.light).darker(250)

        if role == self.ObjectIdRole:
            return item.get("_id", None)

        if role == self.DocumentRole:
            return item.get("_document", None)

        if role == self.subsetColorsRole:
            asset_id = item.get("_id", None)
            return self.asset_colors.get(asset_id) or []

        return super(AssetModel, self).data(index, role)


class RecursiveSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    """Filters to the regex if any of the children matches allow parent"""
    def filterAcceptsRow(self, row, parent):
        regex = self.filterRegExp()
        if not regex.isEmpty():
            pattern = regex.pattern()
            model = self.sourceModel()
            source_index = model.index(row, self.filterKeyColumn(), parent)
            if source_index.isValid():
                # Check current index itself
                key = model.data(source_index, self.filterRole())
                if re.search(pattern, key, re.IGNORECASE):
                    return True

                # Check children
                rows = model.rowCount(source_index)
                for i in range(rows):
                    if self.filterAcceptsRow(i, source_index):
                        return True

                # Otherwise filter it
                return False

        return super(
            RecursiveSortFilterProxyModel, self
        ).filterAcceptsRow(row, parent)


class ProjectModel(QtGui.QStandardItemModel):
    def __init__(
        self, dbcon=None, only_active=True, add_default_project=False,
        *args, **kwargs
    ):
        super(ProjectModel, self).__init__(*args, **kwargs)

        self.dbcon = dbcon

        self._only_active = only_active
        self._add_default_project = add_default_project

        self._default_item = None
        self._items_by_name = {}
        # Model was at least once refreshed
        # - for `set_dbcon` method
        self._refreshed = False

    def set_default_project_available(self, available=True):
        if available is None:
            available = not self._add_default_project

        if self._add_default_project == available:
            return

        self._add_default_project = available
        if not available and self._default_item is not None:
            root_item = self.invisibleRootItem()
            root_item.removeRow(self._default_item.row())
            self._default_item = None

    def set_only_active(self, only_active=True):
        if only_active is None:
            only_active = not self._only_active

        if self._only_active == only_active:
            return

        self._only_active = only_active

        if self._refreshed:
            self.refresh()

    def set_dbcon(self, dbcon):
        """Change mongo connection."""
        self.dbcon = dbcon
        # Trigger refresh if was already refreshed
        if self._refreshed:
            self.refresh()

    def project_name_is_available(self, project_name):
        """Check availability of project name in current items."""
        return project_name in self._items_by_name

    def refresh(self):
        # Change '_refreshed' state
        self._refreshed = True
        new_items = []
        # Add default item to model if should
        if self._add_default_project and self._default_item is None:
            item = QtGui.QStandardItem(DEFAULT_PROJECT_LABEL)
            item.setData(None, PROJECT_NAME_ROLE)
            item.setData(True, PROJECT_IS_ACTIVE_ROLE)
            new_items.append(item)
            self._default_item = item

        project_names = set()
        if self.dbcon is not None:
            for project_doc in self.dbcon.projects(
                projection={"name": 1, "data.active": 1},
                only_active=self._only_active
            ):
                project_name = project_doc["name"]
                project_names.add(project_name)
                if project_name in self._items_by_name:
                    item = self._items_by_name[project_name]
                else:
                    item = QtGui.QStandardItem(project_name)

                    self._items_by_name[project_name] = item
                    new_items.append(item)

                is_active = project_doc.get("data", {}).get("active", True)
                item.setData(project_name, PROJECT_NAME_ROLE)
                item.setData(is_active, PROJECT_IS_ACTIVE_ROLE)

                if not is_active:
                    font = item.font()
                    font.setItalic(True)
                    item.setFont(font)

        root_item = self.invisibleRootItem()
        for project_name in tuple(self._items_by_name.keys()):
            if project_name not in project_names:
                item = self._items_by_name.pop(project_name)
                root_item.removeRow(item.row())

        if new_items:
            root_item.appendRows(new_items)


class ProjectSortFilterProxy(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        super(ProjectSortFilterProxy, self).__init__(*args, **kwargs)
        self._filter_enabled = True

    def lessThan(self, left_index, right_index):
        if left_index.data(PROJECT_NAME_ROLE) is None:
            return True

        if right_index.data(PROJECT_NAME_ROLE) is None:
            return False

        left_is_active = left_index.data(PROJECT_IS_ACTIVE_ROLE)
        right_is_active = right_index.data(PROJECT_IS_ACTIVE_ROLE)
        if right_is_active == left_is_active:
            return super(ProjectSortFilterProxy, self).lessThan(
                left_index, right_index
            )

        if left_is_active:
            return True
        return False

    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        if self._filter_enabled:
            result = self._custom_index_filter(index)
            if result is not None:
                return result

        return super(ProjectSortFilterProxy, self).filterAcceptsRow(
            source_row, source_parent
        )

    def _custom_index_filter(self, index):
        is_active = bool(index.data(PROJECT_IS_ACTIVE_ROLE))

        return is_active

    def is_filter_enabled(self):
        return self._filter_enabled

    def set_filter_enabled(self, value):
        self._filter_enabled = value
        self.invalidateFilter()
