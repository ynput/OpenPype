from Qt import QtWidgets, QtCore, QtGui


class VersionsWidget(QtWidgets.QWidget):
    def __init__(self, controller, parent):
        super(VersionsWidget, self).__init__(parent)

        versions_view = QtWidgets.QTreeView(self)
        versions_model = QtGui.QStandardItemModel()
        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setSourceModel(versions_model)
        versions_view.setModel(proxy_model)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(versions_view, 1)

        controller.event_system.add_callback(
            "versions.refresh.started", self._on_version_refresh_start
        )
        controller.event_system.add_callback(
            "versions.refresh.finished", self._on_version_refresh_finish
        )

        self._versions_view = versions_view
        self._versions_model = versions_model
        self._proxy_model = proxy_model

        self._controller = controller

    def _on_version_refresh_start(self):
        self._versions_model.clear()

    def _on_version_refresh_finish(self):
        subset_items = (
            self._controller.get_current_containers_subset_items()
        )
        new_items = []
        for subset_item in subset_items:
            new_items.append(QtGui.QStandardItem(subset_item.subset_name))

        self._versions_model.clear()
        root_item = self._versions_model.invisibleRootItem()
        if new_items:
            root_item.appendRows(new_items)
