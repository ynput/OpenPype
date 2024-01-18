import collections
import re
import logging
import uuid
import copy

from collections import defaultdict

from qtpy import QtCore, QtGui
import qtawesome

from openpype.client import (
    get_assets,
    get_subsets,
    get_versions,
    get_last_version_by_subset_id,
    get_representations,
)
from openpype.pipeline import (
    get_current_project_name,
    schema,
    HeroVersionType,
)
from openpype.style import get_default_entity_icon_color
from openpype.tools.utils.models import TreeModel, Item
from openpype.tools.ayon_utils.widgets import get_qt_icon


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
            provider: get_qt_icon(icon_def)
            for provider, icon_def in site_icons.items()
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
            if column_name == "active_site":
                progress = item.get("active_site_progress", 0)
            elif column_name == "remote_site":
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

    def refresh(self, selected=None, containers=None):
        """Refresh the model"""

        # for debugging or testing, injecting items from outside
        if containers is None:
            containers = self._controller.get_containers()

        self.clear()
        if not selected or not self._hierarchy_view:
            self._add_containers(containers)
            return

        # Filter by cherry-picked items
        self._add_containers((
            container
            for container in containers
            if container["objectName"] in selected
        ))

    def _add_containers(self, containers, parent=None):
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
            containers (generator): Container items.
            parent (Item, optional): Set this item as parent for the added
              items when provided. Defaults to the root of the model.

        Returns:
            node.Item: root node which has children added based on the data
        """

        project_name = get_current_project_name()

        self.beginResetModel()

        # Group by representation
        grouped = defaultdict(lambda: {"containers": list()})
        for container in containers:
            repre_id = container["representation"]
            grouped[repre_id]["containers"].append(container)

        (
            repres_by_id,
            versions_by_id,
            products_by_id,
            folders_by_id,
        ) = self._query_entities(project_name, set(grouped.keys()))
        # Add to model
        not_found = defaultdict(list)
        not_found_ids = []
        for repre_id, group_dict in sorted(grouped.items()):
            group_containers = group_dict["containers"]
            representation = repres_by_id.get(repre_id)
            if not representation:
                not_found["representation"].extend(group_containers)
                not_found_ids.append(repre_id)
                continue

            version = versions_by_id.get(representation["parent"])
            if not version:
                not_found["version"].extend(group_containers)
                not_found_ids.append(repre_id)
                continue

            product = products_by_id.get(version["parent"])
            if not product:
                not_found["product"].extend(group_containers)
                not_found_ids.append(repre_id)
                continue

            folder = folders_by_id.get(product["parent"])
            if not folder:
                not_found["folder"].extend(group_containers)
                not_found_ids.append(repre_id)
                continue

            group_dict.update({
                "representation": representation,
                "version": version,
                "subset": product,
                "asset": folder
            })

        for _repre_id in not_found_ids:
            grouped.pop(_repre_id)

        for where, group_containers in not_found.items():
            # create the group header
            group_node = Item()
            name = "< NOT FOUND - {} >".format(where)
            group_node["Name"] = name
            group_node["representation"] = name
            group_node["count"] = len(group_containers)
            group_node["isGroupNode"] = False
            group_node["isNotSet"] = True

            self.add_child(group_node, parent=parent)

            for container in group_containers:
                item_node = Item()
                item_node.update(container)
                item_node["Name"] = container.get("objectName", "NO NAME")
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
            group_containers = group_dict["containers"]
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
            group_node["count"] = len(group_containers)
            group_node["isGroupNode"] = True
            group_node["group"] = subset["data"].get("subsetGroup")

            # Site sync specific data
            progress = progress_by_id[repre_id]
            group_node.update(sites_info)
            group_node["active_site_progress"] = progress["active_site"]
            group_node["remote_site_progress"] = progress["remote_site"]

            self.add_child(group_node, parent=parent)

            for container in group_containers:
                item_node = Item()
                item_node.update(container)

                # store the current version on the item
                item_node["version"] = version["name"]

                # Remapping namespace to item name.
                # Noted that the name key is capital "N", by doing this, we
                # can view namespace in GUI without changing container data.
                item_node["Name"] = container["namespace"]

                self.add_child(item_node, parent=group_node)

        self.endResetModel()

        return self._root_item

    def _query_entities(self, project_name, repre_ids):
        """Query entities for representations from containers.

        Returns:
            tuple[dict, dict, dict, dict]: Representation, version, product
                and folder documents by id.
        """

        repres_by_id = {}
        versions_by_id = {}
        products_by_id = {}
        folders_by_id = {}
        output = (
            repres_by_id,
            versions_by_id,
            products_by_id,
            folders_by_id,
        )

        filtered_repre_ids = set()
        for repre_id in repre_ids:
            # Filter out invalid representation ids
            # NOTE: This is added because scenes from OpenPype did contain
            #   ObjectId from mongo.
            try:
                uuid.UUID(repre_id)
                filtered_repre_ids.add(repre_id)
            except ValueError:
                continue
        if not filtered_repre_ids:
            return output

        repre_docs = get_representations(project_name, repre_ids)
        repres_by_id.update({
            repre_doc["_id"]: repre_doc
            for repre_doc in repre_docs
        })
        version_ids = {
            repre_doc["parent"] for repre_doc in repres_by_id.values()
        }
        if not version_ids:
            return output

        version_docs = get_versions(project_name, version_ids, hero=True)
        versions_by_id.update({
            version_doc["_id"]: version_doc
            for version_doc in version_docs
        })
        hero_versions_by_subversion_id = collections.defaultdict(list)
        for version_doc in versions_by_id.values():
            if version_doc["type"] != "hero_version":
                continue
            subversion = version_doc["version_id"]
            hero_versions_by_subversion_id[subversion].append(version_doc)

        if hero_versions_by_subversion_id:
            subversion_ids = set(
                hero_versions_by_subversion_id.keys()
            )
            subversion_docs = get_versions(project_name, subversion_ids)
            for subversion_doc in subversion_docs:
                subversion_id = subversion_doc["_id"]
                subversion_ids.discard(subversion_id)
                h_version_docs = hero_versions_by_subversion_id[subversion_id]
                for version_doc in h_version_docs:
                    version_doc["name"] = HeroVersionType(
                        subversion_doc["name"]
                    )
                    version_doc["data"] = copy.deepcopy(
                        subversion_doc["data"]
                    )

            for subversion_id in subversion_ids:
                h_version_docs = hero_versions_by_subversion_id[subversion_id]
                for version_doc in h_version_docs:
                    versions_by_id.pop(version_doc["_id"])

        product_ids = {
            version_doc["parent"]
            for version_doc in versions_by_id.values()
        }
        if not product_ids:
            return output
        product_docs = get_subsets(project_name, product_ids)
        products_by_id.update({
            product_doc["_id"]: product_doc
            for product_doc in product_docs
        })
        folder_ids = {
            product_doc["parent"]
            for product_doc in products_by_id.values()
        }
        if not folder_ids:
            return output

        folder_docs = get_assets(project_name, folder_ids)
        folders_by_id.update({
            folder_doc["_id"]: folder_doc
            for folder_doc in folder_docs
        })
        return output


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
