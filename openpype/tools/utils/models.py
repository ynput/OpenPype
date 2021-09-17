import re
import time
import logging
import collections

import Qt
from Qt import QtCore, QtGui
from avalon.vendor import qtawesome
from avalon import style, io
from . import lib

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


class TasksModel(TreeModel):
    """A model listing the tasks combined for a list of assets"""

    Columns = ["name", "count"]

    def __init__(self, dbcon, parent=None):
        super(TasksModel, self).__init__(parent=parent)
        self.dbcon = dbcon
        self._num_assets = 0
        self._icons = {
            "__default__": qtawesome.icon(
                "fa.male",
                color=style.colors.default
            ),
            "__no_task__": qtawesome.icon(
                "fa.exclamation-circle",
                color=style.colors.mid
            )
        }

        self._refresh_task_icons()

    def _refresh_task_icons(self):
        # Get the project configured icons from database
        project = self.dbcon.find_one({"type": "project"}, {"config.tasks"})
        tasks = project["config"].get("tasks", {})
        for task_name, task in tasks.items():
            icon_name = task.get("icon", None)
            if icon_name:
                icon = qtawesome.icon(
                    "fa.{}".format(icon_name),
                    color=style.colors.default
                )
                self._icons[task_name] = icon

    def set_assets(self, asset_ids=None, asset_docs=None):
        """Set assets to track by their database id

        Arguments:
            asset_ids (list): List of asset ids.
            asset_docs (list): List of asset entities from MongoDB.

        """

        if asset_docs is None and asset_ids is not None:
            # prepare filter query
            _filter = {"type": "asset", "_id": {"$in": asset_ids}}
            _projection = {"data.tasks"}

            # find assets in db by query
            asset_docs = list(self.dbcon.find(_filter, _projection))
            db_assets_ids = [asset["_id"] for asset in asset_docs]

            # check if all assets were found
            not_found = [
                str(a_id) for a_id in asset_ids if a_id not in db_assets_ids
            ]

            assert not not_found, "Assets not found by id: {0}".format(
                ", ".join(not_found)
            )

        if asset_docs is None:
            asset_docs = list()

        self._num_assets = len(asset_docs)

        tasks = collections.Counter()
        for asset_doc in asset_docs:
            asset_tasks = asset_doc.get("data", {}).get("tasks", {})
            tasks.update(asset_tasks.keys())

        self.clear()
        self.beginResetModel()

        default_icon = self._icons["__default__"]

        if not tasks:
            no_task_icon = self._icons["__no_task__"]
            item = Item({
                "name": "No task",
                "count": 0,
                "icon": no_task_icon,
                "enabled": False,
            })

            self.add_child(item)

        else:
            for task, count in sorted(tasks.items()):
                icon = self._icons.get(task, default_icon)

                item = Item({
                    "name": task,
                    "count": count,
                    "icon": icon
                })

                self.add_child(item)

        self.endResetModel()

    def headerData(self, section, orientation, role):
        # Override header for count column to show amount of assets
        # it is listing the tasks for
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                if section == 0:
                    return "Tasks"
                elif section == 1:  # count column
                    return "count ({0})".format(self._num_assets)

        return super(TasksModel, self).headerData(section, orientation, role)

    def data(self, index, role):
        if not index.isValid():
            return

        # Add icon to the first column
        if role == QtCore.Qt.DecorationRole:
            if index.column() == 0:
                return index.internalPointer()["icon"]

        return super(TasksModel, self).data(index, role)


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
