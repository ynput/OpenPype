import re

from ...vendor.Qt import QtCore

from . import lib


class FilterProxyModel(QtCore.QSortFilterProxyModel):
    """Filter model to where key column's value is in the filtered tags"""

    def __init__(self, *args, **kwargs):
        super(FilterProxyModel, self).__init__(*args, **kwargs)
        self._filter_outdated = False
        self._hierarchy_view = False

    def filterAcceptsRow(self, row, parent):

        model = self.sourceModel()
        source_index = model.index(row,
                                   self.filterKeyColumn(),
                                   parent)

        # Always allow bottom entries (individual containers), since their
        # parent group hidden if it wouldn't have been validated.
        rows = model.rowCount(source_index)
        if not rows:
            return True

        # Filter by regex
        if not self.filterRegExp().isEmpty():
            pattern = re.escape(self.filterRegExp().pattern())

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
        is_outdated = outdated(node)

        if is_outdated:
            return True

        elif self._hierarchy_view:
            for _node in lib.walk_hierarchy(node):
                if outdated(_node):
                    return True
            return False
        else:
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

        if not matches(row, parent, pattern):
            # Also allow if any of the children matches
            source_index = model.index(row, column, parent)
            rows = model.rowCount(source_index)

            if not any(matches(i, source_index, pattern)
                       for i in range(rows)):

                if self._hierarchy_view:
                    for i in range(rows):
                        child_i = model.index(i, column, source_index)
                        child_rows = model.rowCount(child_i)
                        return any(self._matches(ch_i, child_i, pattern)
                                   for ch_i in range(child_rows))

                else:
                    return False

        return True
