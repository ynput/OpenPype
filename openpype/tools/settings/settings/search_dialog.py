import re
import collections

from Qt import QtCore, QtWidgets, QtGui

ENTITY_LABEL_ROLE = QtCore.Qt.UserRole + 1
ENTITY_PATH_ROLE = QtCore.Qt.UserRole + 2


def get_entity_children(entity):
    # TODO find better way how to go through all children
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
            compiled_regex = re.compile(pattern, re.IGNORECASE)
            source_model = self.sourceModel()

            # Check current index itself in all columns
            source_index = source_model.index(row, 0, parent)
            if source_index.isValid():
                for role in (ENTITY_PATH_ROLE, ENTITY_LABEL_ROLE):
                    value = source_model.data(source_index, role)
                    if value and compiled_regex.search(value):
                        return True
            return False

        return super(
            RecursiveSortFilterProxyModel, self
        ).filterAcceptsRow(row, parent)


class SearchEntitiesDialog(QtWidgets.QDialog):
    path_clicked = QtCore.Signal(str)

    def __init__(self, parent):
        super(SearchEntitiesDialog, self).__init__(parent=parent)

        self.setWindowTitle("Search Settings")

        filter_edit = QtWidgets.QLineEdit(self)
        filter_edit.setPlaceholderText("Search...")

        model = EntityTreeModel()
        proxy = RecursiveSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setDynamicSortFilter(True)

        view = QtWidgets.QTreeView(self)
        view.setAllColumnsShowFocus(True)
        view.setSortingEnabled(True)
        view.setModel(proxy)
        model.setColumnCount(3)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(filter_edit)
        layout.addWidget(view)

        filter_changed_timer = QtCore.QTimer()
        filter_changed_timer.setInterval(200)
        filter_changed_timer.setSingleShot(True)

        view.selectionModel().selectionChanged.connect(
            self._on_selection_change
        )
        filter_changed_timer.timeout.connect(self._on_filter_timer)
        filter_edit.textChanged.connect(self._on_filter_changed)

        self._filter_edit = filter_edit
        self._model = model
        self._proxy = proxy
        self._view = view
        self._filter_changed_timer = filter_changed_timer

        self._first_show = True

    def set_root_entity(self, entity):
        self._model.set_root_entity(entity)
        self._view.resizeColumnToContents(0)

    def showEvent(self, event):
        super(SearchEntitiesDialog, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.resize(700, 500)

    def _on_filter_changed(self, txt):
        self._filter_changed_timer.start()

    def _on_filter_timer(self):
        text = self._filter_edit.text()
        self._proxy.setFilterRegExp(text)

        # WARNING This expanding and resizing is relatively slow.
        self._view.expandAll()
        self._view.resizeColumnToContents(0)

    def _on_selection_change(self):
        current = self._view.currentIndex()
        path = current.data(ENTITY_PATH_ROLE)
        self.path_clicked.emit(path)


class EntityTreeModel(QtGui.QStandardItemModel):
    def __init__(self, *args, **kwargs):
        super(EntityTreeModel, self).__init__(*args, **kwargs)
        self.setColumnCount(3)

    def data(self, index, role=None):
        if role is None:
            role = QtCore.Qt.DisplayRole

        col = index.column()
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            if col == 0:
                pass
            elif col == 1:
                role = ENTITY_LABEL_ROLE
            elif col == 2:
                role = ENTITY_PATH_ROLE

        if col > 0:
            index = self.index(index.row(), 0, index.parent())
        return super(EntityTreeModel, self).data(index, role)

    def flags(self, index):
        if index.column() > 0:
            index = self.index(index.row(), 0, index.parent())
        return super(EntityTreeModel, self).flags(index)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if section == 0:
                return "Key"
            elif section == 1:
                return "Label"
            elif section == 2:
                return "Path"
            return ""
        return super(EntityTreeModel, self).headerData(
            section, orientation, role
        )

    def set_root_entity(self, root_entity):
        parent = self.invisibleRootItem()
        parent.removeRows(0, parent.rowCount())
        if not root_entity:
            return

        # We don't want to see the root entity so we directly add its children
        fill_queue = collections.deque()
        fill_queue.append((root_entity, parent))
        cols = self.columnCount()
        while fill_queue:
            parent_entity, parent_item = fill_queue.popleft()
            child_items = []
            for child in get_entity_children(parent_entity):
                label = child.label
                path = child.path
                key = path.split("/")[-1]
                item = QtGui.QStandardItem(key)
                item.setEditable(False)
                item.setData(label, ENTITY_LABEL_ROLE)
                item.setData(path, ENTITY_PATH_ROLE)
                item.setColumnCount(cols)
                child_items.append(item)
                fill_queue.append((child, item))

            if child_items:
                parent_item.appendRows(child_items)
