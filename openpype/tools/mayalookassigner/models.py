from collections import defaultdict

from Qt import QtCore
import qtawesome

from openpype.tools.utils import models
from openpype.style import get_default_entity_icon_color


class AssetModel(models.TreeModel):

    Columns = ["label"]

    def __init__(self, *args, **kwargs):
        super(AssetModel, self).__init__(*args, **kwargs)

        self._icon_color = get_default_entity_icon_color()

    def add_items(self, items):
        """
        Add items to model with needed data
        Args:
            items(list): collection of item data

        Returns:
            None
        """

        self.beginResetModel()

        # Add the items sorted by label
        sorter = lambda x: x["label"]

        for item in sorted(items, key=sorter):

            asset_item = models.Item()
            asset_item.update(item)
            asset_item["icon"] = "folder"

            # Add namespace children
            namespaces = item["namespaces"]
            for namespace in sorted(namespaces):
                child = models.Item()
                child.update(item)
                child.update({
                    "label": (namespace if namespace != ":"
                              else "(no namespace)"),
                    "namespace": namespace,
                    "looks": item["looks"],
                    "icon": "folder-o"
                })
                asset_item.add_child(child)

            self.add_child(asset_item)

        self.endResetModel()

    def data(self, index, role):

        if not index.isValid():
            return

        if role == models.TreeModel.ItemRole:
            node = index.internalPointer()
            return node

        # Add icon
        if role == QtCore.Qt.DecorationRole:
            if index.column() == 0:
                node = index.internalPointer()
                icon = node.get("icon")
                if icon:
                    return qtawesome.icon(
                        "fa.{0}".format(icon),
                        color=self._icon_color
                    )

        return super(AssetModel, self).data(index, role)


class LookModel(models.TreeModel):
    """Model displaying a list of looks and matches for assets"""

    Columns = ["label", "match"]

    def add_items(self, items):
        """Add items to model with needed data

        An item exists of:
            {
                "subset": 'name of subset',
                "asset": asset_document
            }

        Args:
            items(list): collection of item data

        Returns:
            None
        """

        self.beginResetModel()

        # Collect the assets per look name (from the items of the AssetModel)
        look_subsets = defaultdict(list)
        for asset_item in items:
            asset = asset_item["asset"]
            for look in asset_item["looks"]:
                look_subsets[look["name"]].append(asset)

        for subset in sorted(look_subsets.keys()):
            assets = look_subsets[subset]

            # Define nice label without "look" prefix for readability
            label = subset if not subset.startswith("look") else subset[4:]

            item_node = models.Item()
            item_node["label"] = label
            item_node["subset"] = subset

            # Amount of matching assets for this look
            item_node["match"] = len(assets)

            # Store the assets that have this subset available
            item_node["assets"] = assets

            self.add_child(item_node)

        self.endResetModel()
