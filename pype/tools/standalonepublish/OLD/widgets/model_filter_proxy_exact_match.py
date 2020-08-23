from Qt import QtCore


class ExactMatchesFilterProxyModel(QtCore.QSortFilterProxyModel):
    """Filter model to where key column's value is in the filtered tags"""

    def __init__(self, *args, **kwargs):
        super(ExactMatchesFilterProxyModel, self).__init__(*args, **kwargs)
        self._filters = set()

    def setFilters(self, filters):
        self._filters = set(filters)

    def filterAcceptsRow(self, source_row, source_parent):

        # No filter
        if not self._filters:
            return True

        else:
            model = self.sourceModel()
            column = self.filterKeyColumn()
            idx = model.index(source_row, column, source_parent)
            data = model.data(idx, self.filterRole())
            if data in self._filters:
                return True
            else:
                return False
