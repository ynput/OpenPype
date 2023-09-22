from qtpy import QtWidgets, QtGui, QtCore

from openpype.tools.ayon_utils.widgets import get_qt_icon

PRODUCT_TYPE_ROLE = QtCore.Qt.UserRole + 1


class ProductTypesQtModel(QtGui.QStandardItemModel):
    refreshed = QtCore.Signal()
    filter_changed = QtCore.Signal()

    def __init__(self, controller):
        super(ProductTypesQtModel, self).__init__()
        self._controller = controller

        self._refreshing = False
        self._bulk_change = False
        self._items_by_name = {}

    def is_refreshing(self):
        return self._refreshing

    def get_filter_info(self):
        """Product types filtering info.

        Returns:
            dict[str, bool]: Filtering value by product type name. False value
                means to hide product type.
        """

        return {
            name: item.checkState() == QtCore.Qt.Checked
            for name, item in self._items_by_name.items()
        }

    def refresh(self, project_name):
        self._refreshing = True
        product_type_items = self._controller.get_product_type_items(
            project_name)

        items_to_remove = set(self._items_by_name.keys())
        new_items = []
        for product_type_item in product_type_items:
            name = product_type_item.name
            items_to_remove.discard(name)
            item = self._items_by_name.get(product_type_item.name)
            if item is None:
                item = QtGui.QStandardItem(name)
                item.setData(name, PRODUCT_TYPE_ROLE)
                item.setEditable(False)
                item.setCheckable(True)
                new_items.append(item)
                self._items_by_name[name] = item

            item.setCheckState(
                QtCore.Qt.Checked
                if product_type_item.checked
                else QtCore.Qt.Unchecked
            )
            icon = get_qt_icon(product_type_item.icon)
            item.setData(icon, QtCore.Qt.DecorationRole)

        root_item = self.invisibleRootItem()
        if new_items:
            root_item.appendRows(new_items)

        for name in items_to_remove:
            item = self._items_by_name.pop(name)
            root_item.removeRow(item.row())

        self._refreshing = False
        self.refreshed.emit()

    def setData(self, index, value, role=None):
        checkstate_changed = False
        if role is None:
            role = QtCore.Qt.EditRole
        elif role == QtCore.Qt.CheckStateRole:
            checkstate_changed = True
        output = super(ProductTypesQtModel, self).setData(index, value, role)
        if checkstate_changed and not self._bulk_change:
            self.filter_changed.emit()
        return output

    def change_state_for_all(self, checked):
        if self._items_by_name:
            self.change_states(checked, self._items_by_name.keys())

    def change_states(self, checked, product_types):
        product_types = set(product_types)
        if not product_types:
            return

        if checked is None:
            state = None
        elif checked:
            state = QtCore.Qt.Checked
        else:
            state = QtCore.Qt.Unchecked

        self._bulk_change = True

        changed = False
        for product_type in product_types:
            item = self._items_by_name.get(product_type)
            if item is None:
                continue
            new_state = state
            item_checkstate = item.checkState()
            if new_state is None:
                if item_checkstate == QtCore.Qt.Checked:
                    new_state = QtCore.Qt.Unchecked
                else:
                    new_state = QtCore.Qt.Checked
            elif item_checkstate == new_state:
                continue
            changed = True
            item.setCheckState(new_state)

        self._bulk_change = False

        if changed:
            self.filter_changed.emit()


class ProductTypesView(QtWidgets.QListView):
    filter_changed = QtCore.Signal()

    def __init__(self, controller, parent):
        super(ProductTypesView, self).__init__(parent)

        self.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.setAlternatingRowColors(True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        product_types_model = ProductTypesQtModel(controller)
        product_types_proxy_model = QtCore.QSortFilterProxyModel()
        product_types_proxy_model.setSourceModel(product_types_model)

        self.setModel(product_types_proxy_model)

        product_types_model.refreshed.connect(self._on_refresh_finished)
        product_types_model.filter_changed.connect(self._on_filter_change)
        self.customContextMenuRequested.connect(self._on_context_menu)

        controller.register_event_callback(
            "selection.project.changed",
            self._on_project_change
        )

        self._controller = controller

        self._product_types_model = product_types_model
        self._product_types_proxy_model = product_types_proxy_model

    def get_filter_info(self):
        return self._product_types_model.get_filter_info()

    def _on_project_change(self, event):
        project_name = event["project_name"]
        self._product_types_model.refresh(project_name)

    def _on_refresh_finished(self):
        self.filter_changed.emit()

    def _on_filter_change(self):
        if not self._product_types_model.is_refreshing():
            self.filter_changed.emit()

    def _change_selection_state(self, checkstate):
        selection_model = self.selectionModel()
        product_types = {
            index.data(PRODUCT_TYPE_ROLE)
            for index in selection_model.selectedIndexes()
        }
        product_types.discard(None)
        self._product_types_model.change_states(checkstate, product_types)

    def _on_enable_all(self):
        self._product_types_model.change_state_for_all(True)

    def _on_disable_all(self):
        self._product_types_model.change_state_for_all(False)

    def _on_context_menu(self, pos):
        menu = QtWidgets.QMenu(self)

        # Add enable all action
        action_check_all = QtWidgets.QAction(menu)
        action_check_all.setText("Enable All")
        action_check_all.triggered.connect(self._on_enable_all)
        # Add disable all action
        action_uncheck_all = QtWidgets.QAction(menu)
        action_uncheck_all.setText("Disable All")
        action_uncheck_all.triggered.connect(self._on_disable_all)

        menu.addAction(action_check_all)
        menu.addAction(action_uncheck_all)

        # Get mouse position
        global_pos = self.viewport().mapToGlobal(pos)
        menu.exec_(global_pos)

    def event(self, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Space:
                self._change_selection_state(None)
                return True

            if event.key() == QtCore.Qt.Key_Backspace:
                self._change_selection_state(False)
                return True

            if event.key() == QtCore.Qt.Key_Return:
                self._change_selection_state(True)
                return True

        return super(ProductTypesView, self).event(event)
