import re
import logging

from collections import defaultdict

from qtpy import QtCore, QtGui
import qtawesome

from openpype.host import ILoadHost
from openpype.client import (
    get_asset_by_id,
    get_subset_by_id,
    get_version_by_id,
    get_last_version_by_subset_id,
    get_representation_by_id,
)
from openpype.pipeline import (
    get_current_project_name,
    schema,
    HeroVersionType,
)
from openpype.style import get_default_entity_icon_color
from openpype.tools.utils.models import TreeModel, Item


def walk_hierarchy(node):
    """Recursively yield group node."""
    for child in node.children():
        if child.get("isGroupNode"):
            yield child

        for _child in walk_hierarchy(child):
            yield _child


class InventoryModel(TreeModel):
    """The model for the inventory"""

    Columns = [
        "Name",
        "version",
        "count",
        "family",
        "group",
        "loader",
        "objectName",
        "active_site",
        "remote_site",
    ]
    active_site_col = Columns.index("active_site")
    remote_site_col = Columns.index("remote_site")

    OUTDATED_COLOR = QtGui.QColor(235, 30, 30)
    CHILD_OUTDATED_COLOR = QtGui.QColor(200, 160, 30)
    GRAYOUT_COLOR = QtGui.QColor(160, 160, 160)

    UniqueRole = QtCore.Qt.UserRole + 2     # unique label role

    def __init__(self, controller, parent=None):
        super(InventoryModel, self).__init__(parent)
        self.log = logging.getLogger(self.__class__.__name__)

        self._controller = controller

        self._hierarchy_view = False

        self._default_icon_color = get_default_entity_icon_color()

        site_icons = self._controller.get_site_provider_icons()

        self._site_icons = {
            provider: QtGui.QIcon(icon_path)
            for provider, icon_path in site_icons.items()
        }

    def outdated(self, item):
        value = item.get("version")
        if isinstance(value, HeroVersionType):
            return False

        if item.get("version") == item.get("highest_version"):
            return False
        return True

    def data(self, index, role):
        if not index.isValid():
            return

        item = index.internalPointer()

        if role == QtCore.Qt.FontRole:
            # Make top-level entries bold
            if item.get("isGroupNode") or item.get("isNotSet"):  # group-item
                font = QtGui.QFont()
                font.setBold(True)
                return font

        if role == QtCore.Qt.ForegroundRole:
            # Set the text color to the OUTDATED_COLOR when the
            # collected version is not the same as the highest version
            key = self.Columns[index.column()]
            if key == "version":  # version
                if item.get("isGroupNode"):  # group-item
                    if self.outdated(item):
                        return self.OUTDATED_COLOR

                    if self._hierarchy_view:
                        # If current group is not outdated, check if any
                        # outdated children.
                        for _node in walk_hierarchy(item):
                            if self.outdated(_node):
                                return self.CHILD_OUTDATED_COLOR
                else:

                    if self._hierarchy_view:
                        # Although this is not a group item, we still need
                        # to distinguish which one contain outdated child.
                        for _node in walk_hierarchy(item):
                            if self.outdated(_node):
                                return self.CHILD_OUTDATED_COLOR.darker(150)

                    return self.GRAYOUT_COLOR

            if key == "Name" and not item.get("isGroupNode"):
                return self.GRAYOUT_COLOR

        # Add icons
        if role == QtCore.Qt.DecorationRole:
            if index.column() == 0:
                # Override color
                color = item.get("color", self._default_icon_color)
                if item.get("isGroupNode"):  # group-item
                    return qtawesome.icon("fa.folder", color=color)
                if item.get("isNotSet"):
                    return qtawesome.icon("fa.exclamation-circle", color=color)

                return qtawesome.icon("fa.file-o", color=color)

            if index.column() == 3:
                # Family icon
                return item.get("familyIcon", None)

            column_name = self.Columns[index.column()]

            if column_name == "group" and item.get("group"):
                return qtawesome.icon("fa.object-group",
                                      color=get_default_entity_icon_color())

            if item.get("isGroupNode"):
                if column_name == "active_site":
                    provider = item.get("active_site_provider")
                    return self._site_icons.get(provider)

                if column_name == "remote_site":
                    provider = item.get("remote_site_provider")
                    return self._site_icons.get(provider)

        if role == QtCore.Qt.DisplayRole and item.get("isGroupNode"):
            column_name = self.Columns[index.column()]
            progress = None
            if column_name == 'active_site':
                progress = item.get("active_site_progress", 0)
            elif column_name == 'remote_site':
                progress = item.get("remote_site_progress", 0)
            if progress is not None:
                return "{}%".format(max(progress, 0) * 100)

        if role == self.UniqueRole:
            return item["representation"] + item.get("objectName", "<none>")

        return super(InventoryModel, self).data(index, role)

    def set_hierarchy_view(self, state):
        """Set whether to display subsets in hierarchy view."""
        state = bool(state)

        if state != self._hierarchy_view:
            self._hierarchy_view = state

    def refresh(self, selected=None, items=None):
        """Refresh the model"""

        # for debugging or testing, injecting items from outside
        if items is None:
            items = self._controller.get_containers()

        self.clear()
        if not selected or not self._hierarchy_view:
            self.add_items(items)
            return

        # Filter by cherry-picked items
        self.add_items((
            item
            for item in items
            if item["objectName"] in selected
        ))

    def add_items(self, items, parent=None):
        """Add the items to the model.

        The items should be formatted similar to `api.ls()` returns, an item
        is then represented as:
            {"filename_v001.ma": [full/filename/of/loaded/filename_v001.ma,
                                  full/filename/of/loaded/filename_v001.ma],
             "nodetype" : "reference",
             "node": "referenceNode1"}

        Note: When performing an additional call to `add_items` it will *not*
            group the new items with previously existing item groups of the
            same type.

        Args:
            items (generator): the items to be processed as returned by `ls()`
            parent (Item, optional): Set this item as parent for the added
              items when provided. Defaults to the root of the model.

        Returns:
            node.Item: root node which has children added based on the data
        """

        # NOTE: @iLLiCiTiT this need refactor
        project_name = get_current_project_name()

        self.beginResetModel()

        # Group by representation
        grouped = defaultdict(lambda: {"items": list()})
        for item in items:
            grouped[item["representation"]]["items"].append(item)

        # Add to model
        not_found = defaultdict(list)
        not_found_ids = []
        for repre_id, group_dict in sorted(grouped.items()):
            group_items = group_dict["items"]
            # Get parenthood per group
            representation = get_representation_by_id(
                project_name, repre_id
            )
            if not representation:
                not_found["representation"].extend(group_items)
                not_found_ids.append(repre_id)
                continue

            version = get_version_by_id(
                project_name, representation["parent"]
            )
            if not version:
                not_found["version"].extend(group_items)
                not_found_ids.append(repre_id)
                continue

            elif version["type"] == "hero_version":
                _version = get_version_by_id(
                    project_name, version["version_id"]
                )
                version["name"] = HeroVersionType(_version["name"])
                version["data"] = _version["data"]

            subset = get_subset_by_id(project_name, version["parent"])
            if not subset:
                not_found["product"].extend(group_items)
                not_found_ids.append(repre_id)
                continue

            asset = get_asset_by_id(project_name, subset["parent"])
            if not asset:
                not_found["folder"].extend(group_items)
                not_found_ids.append(repre_id)
                continue

            group_dict.update({
                "representation": representation,
                "version": version,
                "subset": subset,
                "asset": asset
            })

        for _repre_id in not_found_ids:
            grouped.pop(_repre_id)

        for where, group_items in not_found.items():
            # create the group header
            group_node = Item()
            name = "< NOT FOUND - {} >".format(where)
            group_node["Name"] = name
            group_node["representation"] = name
            group_node["count"] = len(group_items)
            group_node["isGroupNode"] = False
            group_node["isNotSet"] = True

            self.add_child(group_node, parent=parent)

            for item in group_items:
                item_node = Item()
                item_node.update(item)
                item_node["Name"] = item.get("objectName", "NO NAME")
                item_node["isNotFound"] = True
                self.add_child(item_node, parent=group_node)

        # TODO Use product icons
        family_icon = qtawesome.icon(
            "fa.folder", color="#0091B2"
        )
        # Prepare site sync specific data
        progress_by_id = self._controller.get_representations_site_progress(
            set(grouped.keys())
        )
        sites_info = self._controller.get_sites_information()

        for repre_id, group_dict in sorted(grouped.items()):
            group_items = group_dict["items"]
            representation = group_dict["representation"]
            version = group_dict["version"]
            subset = group_dict["subset"]
            asset = group_dict["asset"]

            # Get the primary family
            maj_version, _ = schema.get_schema_version(subset["schema"])
            if maj_version < 3:
                src_doc = version
            else:
                src_doc = subset

            prim_family = src_doc["data"].get("family")
            if not prim_family:
                families = src_doc["data"].get("families")
                if families:
                    prim_family = families[0]

            # Store the highest available version so the model can know
            # whether current version is currently up-to-date.
            highest_version = get_last_version_by_subset_id(
                project_name, version["parent"]
            )

            # create the group header
            group_node = Item()
            group_node["Name"] = "{}_{}: ({})".format(
                asset["name"], subset["name"], representation["name"]
            )
            group_node["representation"] = repre_id
            group_node["version"] = version["name"]
            group_node["highest_version"] = highest_version["name"]
            group_node["family"] = prim_family or ""
            group_node["familyIcon"] = family_icon
            group_node["count"] = len(group_items)
            group_node["isGroupNode"] = True
            group_node["group"] = subset["data"].get("subsetGroup")

            # Site sync specific data
            progress = progress_by_id[repre_id]
            group_node.update(sites_info)
            group_node["active_site_progress"] = progress["active_site"]
            group_node["remote_site_progress"] = progress["remote_site"]

            self.add_child(group_node, parent=parent)

            for item in group_items:
                item_node = Item()
                item_node.update(item)

                # store the current version on the item
                item_node["version"] = version["name"]

                # Remapping namespace to item name.
                # Noted that the name key is capital "N", by doing this, we
                # can view namespace in GUI without changing container data.
                item_node["Name"] = item["namespace"]

                self.add_child(item_node, parent=group_node)

        self.endResetModel()

        return self._root_item


class FilterProxyModel(QtCore.QSortFilterProxyModel):
    """Filter model to where key column's value is in the filtered tags"""

    def __init__(self, *args, **kwargs):
        super(FilterProxyModel, self).__init__(*args, **kwargs)
        self._filter_outdated = False
        self._hierarchy_view = False

    def filterAcceptsRow(self, row, parent):
        model = self.sourceModel()
        source_index = model.index(row, self.filterKeyColumn(), parent)

        # Always allow bottom entries (individual containers), since their
        # parent group hidden if it wouldn't have been validated.
        rows = model.rowCount(source_index)
        if not rows:
            return True

        # Filter by regex
        if hasattr(self, "filterRegExp"):
            regex = self.filterRegExp()
        else:
            regex = self.filterRegularExpression()
        pattern = regex.pattern()
        if pattern:
            pattern = re.escape(pattern)

            if not self._matches(row, parent, pattern):
                return False

        if self._filter_outdated:
            # When filtering to outdated we filter the up to date entries
            # thus we "allow" them when they are outdated
            if not self._is_outdated(row, parent):
                return False

        return True

    def set_filter_outdated(self, state):
        """Set whether to show the outdated entries only."""
        state = bool(state)

        if state != self._filter_outdated:
            self._filter_outdated = bool(state)
            self.invalidateFilter()

    def set_hierarchy_view(self, state):
        state = bool(state)

        if state != self._hierarchy_view:
            self._hierarchy_view = state

    def _is_outdated(self, row, parent):
        """Return whether row is outdated.

        A row is considered outdated if it has "version" and "highest_version"
        data and in the internal data structure, and they are not of an
        equal value.

        """
        def outdated(node):
            version = node.get("version", None)
            highest = node.get("highest_version", None)

            # Always allow indices that have no version data at all
            if version is None and highest is None:
                return True

            # If either a version or highest is present but not the other
            # consider the item invalid.
            if not self._hierarchy_view:
                # Skip this check if in hierarchy view, or the child item
                # node will be hidden even it's actually outdated.
                if version is None or highest is None:
                    return False
            return version != highest

        index = self.sourceModel().index(row, self.filterKeyColumn(), parent)

        # The scene contents are grouped by "representation", e.g. the same
        # "representation" loaded twice is grouped under the same header.
        # Since the version check filters these parent groups we skip that
        # check for the individual children.
        has_parent = index.parent().isValid()
        if has_parent and not self._hierarchy_view:
            return True

        # Filter to those that have the different version numbers
        node = index.internalPointer()
        if outdated(node):
            return True

        if self._hierarchy_view:
            for _node in walk_hierarchy(node):
                if outdated(_node):
                    return True

        return False

    def _matches(self, row, parent, pattern):
        """Return whether row matches regex pattern.

        Args:
            row (int): row number in model
            parent (QtCore.QModelIndex): parent index
            pattern (regex.pattern): pattern to check for in key

        Returns:
            bool

        """
        model = self.sourceModel()
        column = self.filterKeyColumn()
        role = self.filterRole()

        def matches(row, parent, pattern):
            index = model.index(row, column, parent)
            key = model.data(index, role)
            if re.search(pattern, key, re.IGNORECASE):
                return True

        if matches(row, parent, pattern):
            return True

        # Also allow if any of the children matches
        source_index = model.index(row, column, parent)
        rows = model.rowCount(source_index)

        if any(
            matches(idx, source_index, pattern)
            for idx in range(rows)
        ):
            return True

        if not self._hierarchy_view:
            return False

        for idx in range(rows):
            child_index = model.index(idx, column, source_index)
            child_rows = model.rowCount(child_index)
            return any(
                self._matches(child_idx, child_index, pattern)
                for child_idx in range(child_rows)
            )

        return True
