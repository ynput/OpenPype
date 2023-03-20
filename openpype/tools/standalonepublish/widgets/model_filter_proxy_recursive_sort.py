import re
from qtpy import QtCore


class RecursiveSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    """Filters to the regex if any of the children matches allow parent"""
    def filterAcceptsRow(self, row, parent):
        if hasattr(self, "filterRegExp"):
            regex = self.filterRegExp()
        else:
            regex = self.filterRegularExpression()
        pattern = regex.pattern()
        if pattern:
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

        return super(RecursiveSortFilterProxyModel,
                     self).filterAcceptsRow(row, parent)
