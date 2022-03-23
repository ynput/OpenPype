import logging
import collections

from Qt import QtCore, QtGui
import qtawesome

from openpype.style import (
    get_default_entity_icon_color,
    get_deprecated_entity_font_color,
)

from . import TreeModel, Node

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


class AssetModel(TreeModel):
    """A model listing assets in the active project.

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

    def __init__(self, dbcon, parent=None):
        super(AssetModel, self).__init__(parent=parent)
        self.dbcon = dbcon

        self._default_asset_icon_color = QtGui.QColor(
            get_default_entity_icon_color()
        )
        self._deprecated_asset_font_color = QtGui.QColor(
            get_deprecated_entity_font_color()
        )

        self.refresh()

    def _add_hierarchy(self, assets, parent=None):
        """Add the assets that are related to the parent as children items.

        This method does *not* query the database. These instead are queried
        in a single batch upfront as an optimization to reduce database
        queries. Resulting in up to 10x speed increase.

        Args:
            assets (dict): All assets from current project.
        """
        parent_id = parent["_id"] if parent else None
        current_assets = assets.get(parent_id, list())

        for asset in current_assets:
            # get label from data, otherwise use name
            data = asset.get("data", {})
            label = data.get("label", asset["name"])
            tags = data.get("tags", [])

            # store for the asset for optimization
            deprecated = "deprecated" in tags

            node = Node({
                "_id": asset["_id"],
                "name": asset["name"],
                "label": label,
                "type": asset["type"],
                "tags": ", ".join(tags),
                "deprecated": deprecated,
                "_document": asset
            })
            self.add_child(node, parent=parent)

            # Add asset's children recursively if it has children
            if asset["_id"] in assets:
                self._add_hierarchy(assets, parent=node)

    def refresh(self):
        """Refresh the data for the model."""

        self.clear()
        if (
            self.dbcon.active_project() is None or
            self.dbcon.active_project() == ''
        ):
            return

        self.beginResetModel()

        # Get all assets in current project sorted by name
        db_assets = self.dbcon.find({"type": "asset"}).sort("name", 1)

        # Group the assets by their visual parent's id
        assets_by_parent = collections.defaultdict(list)
        for asset in db_assets:
            parent_id = asset.get("data", {}).get("visualParent")
            assets_by_parent[parent_id].append(asset)

        # Build the hierarchical tree items recursively
        self._add_hierarchy(
            assets_by_parent,
            parent=None
        )

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
                data = node.get("_document", {}).get("data", {})
                icon = data.get("icon", None)
                color = data.get("color", self._default_asset_icon_color)

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
                    icon = qtawesome.icon(key, color=color)
                    return icon
                except Exception as exception:
                    # Log an error message instead of erroring out completely
                    # when the icon couldn't be created (e.g. invalid name)
                    log.error(exception)

                return

        if role == QtCore.Qt.ForegroundRole:        # font color
            if "deprecated" in node.get("tags", []):
                return QtGui.QColor(self._deprecated_asset_font_color)

        if role == self.ObjectIdRole:
            return node.get("_id", None)

        if role == self.DocumentRole:
            return node.get("_document", None)

        return super(AssetModel, self).data(index, role)
