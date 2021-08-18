import collections

from Qt import QtWidgets, QtCore, QtGui

from constants import (
    INSTANCE_ID_ROLE,
    SORT_VALUE_ROLE
)


class InstanceCardWidget(QtWidgets.QWidget):
    active_changed = QtCore.Signal(str, bool)

    def __init__(self, instance, item, parent):
        super(InstanceCardWidget, self).__init__(parent)

        self.instance = instance
        self.item = item

        subset_name_label = QtWidgets.QLabel(instance.data["subset"], self)
        active_checkbox = QtWidgets.QCheckBox(self)
        active_checkbox.setChecked(instance.data["active"])

        expand_btn = QtWidgets.QToolButton(self)
        expand_btn.setObjectName("ArrowBtn")
        expand_btn.setArrowType(QtCore.Qt.DownArrow)
        expand_btn.setMaximumWidth(14)
        expand_btn.setEnabled(False)

        detail_widget = QtWidgets.QWidget(self)
        detail_widget.setVisible(False)
        self.detail_widget = detail_widget

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addWidget(subset_name_label)
        top_layout.addStretch(1)
        top_layout.addWidget(active_checkbox)
        top_layout.addWidget(expand_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addLayout(top_layout)
        layout.addWidget(detail_widget)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        subset_name_label.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        active_checkbox.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        expand_btn.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        active_checkbox.stateChanged.connect(self._on_active_change)
        expand_btn.clicked.connect(self._on_expend_clicked)

        self.subset_name_label = subset_name_label
        self.active_checkbox = active_checkbox
        self.expand_btn = expand_btn

    def set_active(self, new_value):
        checkbox_value = self.active_checkbox.isChecked()
        instance_value = self.instance.data["active"]

        # First change instance value and them change checkbox
        # - prevent to trigger `active_changed` signal
        if instance_value != new_value:
            self.instance.data["active"] = new_value

        if checkbox_value != new_value:
            self.active_checkbox.setChecked(new_value)

    def update_instance(self, instance):
        self.instance = instance
        self.update_instance_values()

    def update_instance_values(self):
        self.set_active(self.instance.data["active"])

    def _set_expanded(self, expanded=None):
        if expanded is None:
            expanded = not self.detail_widget.isVisible()
        self.detail_widget.setVisible(expanded)
        self.item.setSizeHint(self.sizeHint())

    def showEvent(self, event):
        super(InstanceCardWidget, self).showEvent(event)
        self.item.setSizeHint(self.sizeHint())

    def _on_active_change(self):
        new_value = self.active_checkbox.isChecked()
        old_value = self.instance.data["active"]
        if new_value == old_value:
            return

        self.instance.data["active"] = new_value
        self.active_changed.emit(self.instance.data["uuid"], new_value)

    def _on_expend_clicked(self):
        self._set_expanded()


class _AbstractInstanceView(QtWidgets.QWidget):
    selection_changed = QtCore.Signal()

    def refresh(self):
        raise NotImplementedError((
            "{} Method 'refresh' is not implemented."
        ).format(self.__class__.__name__))

    def get_selected_instances(self):
        raise NotImplementedError((
            "{} Method 'get_selected_instances' is not implemented."
        ).format(self.__class__.__name__))

    def set_selected_instances(self, instances):
        raise NotImplementedError((
            "{} Method 'set_selected_instances' is not implemented."
        ).format(self.__class__.__name__))


class InstanceCardView(_AbstractInstanceView):
    def __init__(self, controller, parent):
        super(InstanceCardView, self).__init__(parent)

        self.controller = controller

        list_widget = QtWidgets.QListWidget(self)
        list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        list_widget.setResizeMode(QtWidgets.QListView.Adjust)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(list_widget, 1)

        list_widget.selectionModel().selectionChanged.connect(
            self._on_selection_change
        )

        self._items_by_id = {}
        self._widgets_by_id = {}

        self.list_widget = list_widget

    def refresh(self):
        instances_by_id = {}
        for instance in self.controller.instances:
            instance_id = instance.data["uuid"]
            instances_by_id[instance_id] = instance

        for instance_id in tuple(self._items_by_id.keys()):
            if instance_id not in instances_by_id:
                item = self._items_by_id.pop(instance_id)
                self.list_widget.removeItemWidget(item)
                widget = self._widgets_by_id.pop(instance_id)
                widget.deleteLater()
                row = self.list_widget.row(item)
                self.list_widget.takeItem(row)

        for instance_id, instance in instances_by_id.items():
            if instance_id in self._items_by_id:
                widget = self._widgets_by_id[instance_id]
                widget.update_instance(instance)

            else:
                item = QtWidgets.QListWidgetItem(self.list_widget)
                widget = InstanceCardWidget(instance, item, self)
                widget.active_changed.connect(self._on_active_changed)
                item.setData(INSTANCE_ID_ROLE, instance_id)
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, widget)
                self._items_by_id[instance_id] = item
                self._widgets_by_id[instance_id] = widget

    def refresh_active_state(self):
        for widget in self._widgets_by_id.values():
            widget.update_instance_values()

    def _on_active_changed(self, changed_instance_id, new_value):
        selected_ids = set()
        found = False
        for item in self.list_widget.selectedItems():
            instance_id = item.data(INSTANCE_ID_ROLE)
            selected_ids.add(instance_id)
            if not found and instance_id == changed_instance_id:
                found = True

        if not found:
            return

        for instance_id in selected_ids:
            widget = self._widgets_by_id.get(instance_id)
            if widget:
                widget.set_active(new_value)

    def _on_selection_change(self, *_args):
        self.selection_changed.emit()

    def get_selected_instances(self):
        instances = []
        for item in self.list_widget.selectedItems():
            instance_id = item.data(INSTANCE_ID_ROLE)
            widget = self._widgets_by_id.get(instance_id)
            if widget:
                instances.append(widget.instance)
        return instances

    def set_selected_instances(self, instances):
        indexes = []
        model = self.list_widget.model()
        for instance in instances:
            instance_id = instance.data["uuid"]
            item = self._items_by_id.get(instance_id)
            if item:
                row = self.list_widget.row(item)
                index = model.index(row, 0)
                indexes.append(index)

        selection_model = self.list_widget.selectionModel()
        first_item = True
        for index in indexes:
            if first_item:
                first_item = False
                select_type = QtCore.QItemSelectionModel.ClearAndSelect
            else:
                select_type = QtCore.QItemSelectionModel.Select
            selection_model.select(index, select_type)


class InstanceListItemWidget(QtWidgets.QWidget):
    active_changed = QtCore.Signal(str, bool)

    def __init__(self, instance, parent):
        super(InstanceListItemWidget, self).__init__(parent)

        self.instance = instance

        subset_name_label = QtWidgets.QLabel(instance.data["subset"], self)
        active_checkbox = QtWidgets.QCheckBox(self)
        active_checkbox.setChecked(instance.data["active"])

        layout = QtWidgets.QHBoxLayout(self)
        content_margins = layout.contentsMargins()
        layout.setContentsMargins(content_margins.left() + 2, 0, 2, 0)
        layout.addWidget(subset_name_label)
        layout.addStretch(1)
        layout.addWidget(active_checkbox)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        subset_name_label.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        active_checkbox.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        active_checkbox.stateChanged.connect(self._on_active_change)

        self.subset_name_label = subset_name_label
        self.active_checkbox = active_checkbox

    def set_active(self, new_value):
        checkbox_value = self.active_checkbox.isChecked()
        instance_value = self.instance.data["active"]

        # First change instance value and them change checkbox
        # - prevent to trigger `active_changed` signal
        if instance_value != new_value:
            self.instance.data["active"] = new_value

        if checkbox_value != new_value:
            self.active_checkbox.setChecked(new_value)

    def update_instance(self, instance):
        self.instance = instance
        self.update_instance_values()

    def update_instance_values(self):
        self.set_active(self.instance.data["active"])

    def _on_active_change(self):
        new_value = self.active_checkbox.isChecked()
        old_value = self.instance.data["active"]
        if new_value == old_value:
            return

        self.instance.data["active"] = new_value
        self.active_changed.emit(self.instance.data["uuid"], new_value)


class InstanceListGroupWidget(QtWidgets.QFrame):
    expand_changed = QtCore.Signal(str, bool)

    def __init__(self, family, parent):
        super(InstanceListGroupWidget, self).__init__(parent)
        self.setObjectName("InstanceListGroupWidget")

        self.family = family
        self._expanded = False

        subset_name_label = QtWidgets.QLabel(family, self)

        expand_btn = QtWidgets.QToolButton(self)
        expand_btn.setObjectName("ArrowBtn")
        expand_btn.setArrowType(QtCore.Qt.RightArrow)
        expand_btn.setMaximumWidth(14)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 2, 0)
        layout.addWidget(
            subset_name_label, 1, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        layout.addWidget(expand_btn)

        # self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        subset_name_label.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        expand_btn.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        expand_btn.clicked.connect(self._on_expand_clicked)

        self.subset_name_label = subset_name_label
        self.expand_btn = expand_btn

    def _on_expand_clicked(self):
        self.expand_changed.emit(self.family, not self._expanded)

    def set_expanded(self, expanded):
        if self._expanded == expanded:
            return

        self._expanded = expanded
        if expanded:
            self.expand_btn.setArrowType(QtCore.Qt.DownArrow)
        else:
            self.expand_btn.setArrowType(QtCore.Qt.RightArrow)


class InstanceListView(_AbstractInstanceView):
    def __init__(self, controller, parent):
        super(InstanceListView, self).__init__(parent)

        self.controller = controller

        instance_view = QtWidgets.QTreeView(self)
        instance_view.setObjectName("InstanceListView")
        instance_view.setHeaderHidden(True)
        instance_view.setIndentation(0)
        instance_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )

        instance_model = QtGui.QStandardItemModel()

        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setSourceModel(instance_model)
        proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        proxy_model.setSortRole(SORT_VALUE_ROLE)
        proxy_model.setFilterKeyColumn(0)
        proxy_model.setDynamicSortFilter(True)

        instance_view.setModel(proxy_model)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(instance_view)

        instance_view.selectionModel().selectionChanged.connect(
            self._on_selection_change
        )
        instance_view.collapsed.connect(self._on_collapse)
        instance_view.expanded.connect(self._on_expand)

        self._group_items = {}
        self._group_widgets = {}
        self._widgets_by_id = {}
        self.instance_view = instance_view
        self.instance_model = instance_model
        self.proxy_model = proxy_model

    def _on_expand(self, index):
        family = index.data(SORT_VALUE_ROLE)
        group_widget = self._group_widgets.get(family)
        if group_widget:
            group_widget.set_expanded(True)

    def _on_collapse(self, index):
        family = index.data(SORT_VALUE_ROLE)
        group_widget = self._group_widgets.get(family)
        if group_widget:
            group_widget.set_expanded(False)

    def refresh(self):
        instances_by_family = collections.defaultdict(list)
        families = set()
        for instance in self.controller.instances:
            family = instance.data["family"]
            families.add(family)
            instances_by_family[family].append(instance)

        new_group_items = []
        for family in families:
            if family in self._group_items:
                continue

            group_item = QtGui.QStandardItem()
            group_item.setData(family, SORT_VALUE_ROLE)
            group_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self._group_items[family] = group_item
            new_group_items.append(group_item)

        sort_at_the_end = False
        root_item = self.instance_model.invisibleRootItem()
        if new_group_items:
            sort_at_the_end = True
            root_item.appendRows(new_group_items)

        for group_item in new_group_items:
            index = self.instance_model.index(
                group_item.row(), group_item.column()
            )
            proxy_index = self.proxy_model.mapFromSource(index)
            family = group_item.data(SORT_VALUE_ROLE)
            widget = InstanceListGroupWidget(family, self.instance_view)
            widget.expand_changed.connect(self._on_group_expand_request)
            self._group_widgets[family] = widget
            self.instance_view.setIndexWidget(proxy_index, widget)

        for family in tuple(self._group_items.keys()):
            if family in families:
                continue

            group_item = self._group_items.pop(family)
            root_item.removeRow(group_item.row())
            widget = self._group_widgets.pop(family)
            widget.deleteLater()

        for family, group_item in self._group_items.items():
            to_remove = set()
            existing_mapping = {}

            group_index = self.instance_model.index(
                group_item.row(), group_item.column()
            )

            for idx in range(group_item.rowCount()):
                index = self.instance_model.index(idx, 0, group_index)
                instance_id = index.data(INSTANCE_ID_ROLE)
                to_remove.add(instance_id)
                existing_mapping[instance_id] = idx

            new_items = []
            new_items_with_instance = []
            for instance in instances_by_family[family]:
                instance_id = instance.data["uuid"]
                if instance_id in to_remove:
                    to_remove.remove(instance_id)
                    widget = self._widgets_by_id[instance_id]
                    widget.update_instance(instance)
                    continue

                item = QtGui.QStandardItem()
                item.setData(instance.data["subset"], SORT_VALUE_ROLE)
                item.setData(instance.data["uuid"], INSTANCE_ID_ROLE)
                new_items.append(item)
                new_items_with_instance.append((item, instance))

            idx_to_remove = []
            for instance_id in to_remove:
                idx_to_remove.append(existing_mapping[instance_id])

            for idx in reversed(sorted(idx_to_remove)):
                group_item.removeRows(idx, 1)

            for instance_id in to_remove:
                widget = self._widgets_by_id.pop(instance_id)
                widget.deleteLater()

            if new_items:
                sort_at_the_end = True

                group_item.appendRows(new_items)

                for item, instance in new_items_with_instance:
                    item_index = self.instance_model.index(
                        item.row(),
                        item.column(),
                        group_index
                    )
                    proxy_index = self.proxy_model.mapFromSource(item_index)
                    widget = InstanceListItemWidget(
                        instance, self.instance_view
                    )
                    self.instance_view.setIndexWidget(proxy_index, widget)
                    self._widgets_by_id[instance.data["uuid"]] = widget

            # Trigger sort at the end of refresh
            if sort_at_the_end:
                self.proxy_model.sort(0)

    def refresh_active_state(self):
        for widget in self._widgets_by_id.values():
            widget.update_instance_values()

    def get_selected_instances(self):
        instances = []
        instances_by_id = {}
        for instance in self.controller.instances:
            instance_id = instance.data["uuid"]
            instances_by_id[instance_id] = instance

        for index in self.instance_view.selectionModel().selectedIndexes():
            instance_id = index.data(INSTANCE_ID_ROLE)
            if instance_id is not None:
                instance = instances_by_id.get(instance_id)
                if instance:
                    instances.append(instance)

        return instances

    def set_selected_instances(self, instances):
        model = self.instance_view.model()
        instance_ids_by_family = collections.defaultdict(set)
        for instance in instances:
            family = instance.data["family"]
            instance_id = instance.data["uuid"]
            instance_ids_by_family[family].add(instance_id)

        indexes = []
        for family, group_item in self._group_items.items():
            selected_ids = instance_ids_by_family[family]
            if not selected_ids:
                continue

            group_index = self.instance_model.index(
                group_item.row(), group_item.column()
            )
            proxy_group_index = self.proxy_model.mapFromSource(group_index)
            has_indexes = False
            for row in range(group_item.rowCount()):
                index = model.index(row, 0, proxy_group_index)
                instance_id = index.data(INSTANCE_ID_ROLE)
                if instance_id in selected_ids:
                    indexes.append(index)
                    has_indexes = True

            if has_indexes:
                self.instance_view.setExpanded(proxy_group_index, True)

        selection_model = self.instance_view.selectionModel()
        first_item = True
        for index in indexes:
            if first_item:
                first_item = False
                select_type = QtCore.QItemSelectionModel.ClearAndSelect
            else:
                select_type = QtCore.QItemSelectionModel.Select
            selection_model.select(index, select_type)

    def _on_selection_change(self, *_args):
        self.selection_changed.emit()

    def _on_group_expand_request(self, family, expanded):
        group_item = self._group_items.get(family)
        if not group_item:
            return

        group_index = self.instance_model.index(
            group_item.row(), group_item.column()
        )
        proxy_index = self.proxy_model.mapFromSource(group_index)
        self.instance_view.setExpanded(proxy_index, expanded)
