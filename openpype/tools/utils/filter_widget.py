from Qt import QtWidgets, QtCore, QtGui

from avalon.vendor import qtawesome
from avalon import style
from .views import DeselectableTreeView
from functools import reduce



class AssetsTasksFilterWidget(QtWidgets.QWidget):
    """Widget filters for asset and task"""

    filter_changed = QtCore.Signal()

    def __init__(self, dbcon, parent=None):
        super(AssetsTasksFilterWidget, self).__init__(parent)

        view = FiltersTreeView() #DeselectableTreeView()
        model = FiltersModel(dbcon, self)
        proxy = FiltersProxy()
        proxy.setSourceModel(model)
        view.setModel(proxy)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(view)

        selection = view.selectionModel()
        selection.selectionChanged.connect(self._on_filter_change)

        self._model = model
        # self._proxy = proxy
        # self._view = view

        self._last_selected_filters = None

    def refresh(self):
        self._model.refresh()

    def get_selected_filters(self):
        print("get_selected_filter NOT IMPLEMENTED!!!!"*5)

    def _on_filter_change(self):
        print("ON FILTER CHANGE!!!")
        self.filter_changed.emit()


class FiltersTreeView(QtWidgets.QTreeView):
     def __init__(self):
        super(FiltersTreeView, self).__init__()

        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)


class FiltersModel(QtGui.QStandardItemModel):
    """"""

    filter_hierarchy = {
        "tasks": "data.tasks",
        # "tasks type": "data.tasks.*.type",
        "assigned to": "data.tasks.*.assigned",
        "parent": "data.parents"
    }

    def __init__(self, dbcon, parent=None):
        super(FiltersModel, self).__init__(parent=parent)

        self.setHorizontalHeaderLabels(['Filters'])

        self.dbcon = dbcon

        self._asset = []
        self._filters = {}

        self.populate()

    def populate(self):
        root_item = self.invisibleRootItem()
        root_item.removeRows(0, root_item.rowCount())

        items = []

        if not self._filters:
            if root_item.rowCount():
                return
            no_filter_item = QtGui.QStandardItem("No Filters Found !")
            items.append(no_filter_item)

        else:
            items = []
            for group, possible_value in self._filters.items():
                value_items = []
                for value in possible_value:
                    value_item = QtGui.QStandardItem(value)
                    value_item.setData("TEST", role=QtCore.Qt.UserRole)
                    value_item.setCheckable(True)
                    value_items.append(value_item)
                if value_items:
                    group_item = QtGui.QStandardItem(group)
                    group_item.appendRows(value_items)
                    items.append(group_item)

        root_item.appendRows(items)

    def refresh(self):
        print("TRY TO REFRESH !!!!"*5)

        self._fetch_assets()

        self._fetch_filters()

        self.populate()

    def _fetch_filters(self):
        if not self._assets:
            self._filters = {}

        assets = list(self.dbcon.find({"type": "asset"}))
        filters = {}

        for visual_name, attr in self.filter_hierarchy.items():
            possible_value = set()
            for asset in assets:

                value = self.get_recursive(asset, attr)
                if isinstance(value, dict):
                    value = list(value.keys())

                if value:
                    possible_value.update(value)

            filters[visual_name] = possible_value
        self._filters = filters

    def _fetch_assets(self):
        if not self.dbcon.Session.get("AVALON_PROJECT"):
            self._assets = {}
        self._assets = list(self.dbcon.find({"type": "asset"}))

    def get_recursive(self, dict_asset, string, result=None):
        result = result or set()

        if "." not in string:
            if dict_asset.get(string):
                result.update(dict_asset.get(string))
                return result
            return result

        key, new_string = string.split(".", 1)

        # Get all possible value if key is *
        if key == "*":
            for i in dict_asset.values():
                return self.get_recursive(i, new_string, result=result)

        return self.get_recursive(dict_asset.get(key, {}), new_string, result=result)


class FiltersProxy(QtCore.QSortFilterProxyModel):
    def filterAcceptsRow(self, row, parent):
        return True

