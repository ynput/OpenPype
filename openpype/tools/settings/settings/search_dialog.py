from functools import partial
import re

from Qt import QtCore, QtWidgets
from openpype.tools.utils.models import TreeModel, Item
from openpype.tools.utils.lib import schedule


def get_entity_children(entity):

    if hasattr(entity, "values"):
        return entity.values()
    return []


class RecursiveSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    """Filters recursively to regex in all columns"""

    def __init__(self):
        super(RecursiveSortFilterProxyModel, self).__init__()

        # Note: Recursive filtering was introduced in Qt 5.10.
        self.setRecursiveFilteringEnabled(True)

    def filterAcceptsRow(self, row, parent):

        if not parent.isValid():
            return False

        regex = self.filterRegExp()
        if not regex.isEmpty() and regex.isValid():
            pattern = regex.pattern()
            source_model = self.sourceModel()

            # Check current index itself in all columns
            for column in range(source_model.columnCount(parent)):
                source_index = source_model.index(row, column, parent)
                if not source_index.isValid():
                    continue

                key = source_model.data(source_index, self.filterRole())
                if not key:
                    continue

                if re.search(pattern, key, re.IGNORECASE):
                    return True

            return False

        return super(RecursiveSortFilterProxyModel,
                     self).filterAcceptsRow(row, parent)


class SearchEntitiesDialog(QtWidgets.QDialog):

    path_clicked = QtCore.Signal(str)

    def __init__(self, entity, parent=None):
        super(SearchEntitiesDialog, self).__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout(self)

        filter_edit = QtWidgets.QLineEdit()
        filter_edit.setPlaceholderText("Search..")

        model = EntityTreeModel()
        proxy = RecursiveSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setDynamicSortFilter(True)
        view = QtWidgets.QTreeView()
        view.setModel(proxy)

        layout.addWidget(filter_edit)
        layout.addWidget(view)

        filter_edit.textChanged.connect(self._on_filter_changed)
        view.selectionModel().selectionChanged.connect(self.on_select)

        view.setAllColumnsShowFocus(True)
        view.setSortingEnabled(True)
        view.sortByColumn(1, QtCore.Qt.AscendingOrder)

        self._model = model
        self._proxy = proxy
        self._view = view

        # Refresh to the passed entity
        model.set_root(entity)

        view.resizeColumnToContents(0)

    def _on_filter_changed(self, txt):
        # Provide slight delay to filtering so user can type quickly
        schedule(partial(self.on_filter_changed, txt), 250, channel="search")

    def on_filter_changed(self, txt):
        self._proxy.setFilterRegExp(txt)

        # WARNING This expanding and resizing is relatively slow.
        self._view.expandAll()
        self._view.resizeColumnToContents(0)

    def on_select(self):
        current = self._view.currentIndex()
        item = current.data(EntityTreeModel.ItemRole)
        self.path_clicked.emit(item["path"])


class EntityTreeModel(TreeModel):

    Columns = ["trail", "label", "key", "path"]

    def add_entity(self, entity, parent=None):

        item = Item()

        # Label and key can sometimes be emtpy so we use the trail from path
        # in the most left column since it's never empty
        item["trail"] = entity.path.rsplit("/", 1)[-1]
        item["label"] = entity.label
        item["key"] = entity.key
        item["path"] = entity.path

        parent.add_child(item)

        for child in get_entity_children(entity):
            self.add_entity(child, parent=item)

    def set_root(self, root_entity):
        self.clear()
        self.beginResetModel()

        # We don't want to see the root entity so we directly add its children
        for child in get_entity_children(root_entity):
            self.add_entity(child, parent=self._root_item)
        self.endResetModel()

