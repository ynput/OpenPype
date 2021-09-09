from Qt import QtWidgets, QtCore

from openpype.widgets.nice_checkbox import NiceCheckbox

from .widgets import (
    AbstractInstanceView,
    ContextWarningLabel
)
from ..constants import (
    INSTANCE_ID_ROLE,
    CONTEXT_ID,
    CONTEXT_LABEL
)


class ContextCardWidget(QtWidgets.QWidget):
    def __init__(self, item, parent):
        super(ContextCardWidget, self).__init__(parent)

        self.item = item

        subset_name_label = QtWidgets.QLabel(CONTEXT_LABEL, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(subset_name_label)
        layout.addStretch(1)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        subset_name_label.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.subset_name_label = subset_name_label

    def showEvent(self, event):
        super(ContextCardWidget, self).showEvent(event)
        self.item.setSizeHint(self.sizeHint())


class InstanceCardWidget(QtWidgets.QWidget):
    active_changed = QtCore.Signal(str, bool)

    def __init__(self, instance, item, parent):
        super(InstanceCardWidget, self).__init__(parent)

        self.instance = instance
        self.item = item

        subset_name_label = QtWidgets.QLabel(instance.data["subset"], self)
        active_checkbox = NiceCheckbox(parent=self)
        active_checkbox.setChecked(instance.data["active"])

        context_warning = ContextWarningLabel(self)
        if instance.has_valid_context:
            context_warning.setVisible(False)

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
        top_layout.addWidget(context_warning)
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
        self.context_warning = context_warning
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
        self.context_warning.setVisible(not self.instance.has_valid_context)

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


class InstanceCardView(AbstractInstanceView):
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

        self._context_widget = None
        self._context_item = None

        self.list_widget = list_widget

    def refresh(self):
        instances_by_id = {}
        for instance in self.controller.instances:
            instance_id = instance.data["uuid"]
            instances_by_id[instance_id] = instance

        if not self._context_item:
            item = QtWidgets.QListWidgetItem(self.list_widget)
            item.setData(INSTANCE_ID_ROLE, CONTEXT_ID)

            widget = ContextCardWidget(item, self)
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

            self._context_item = item
            self._context_widget = widget

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

    def refresh_instance_states(self):
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
            selected_ids = set()
            selected_ids.add(changed_instance_id)

        changed_ids = set()
        for instance_id in selected_ids:
            widget = self._widgets_by_id.get(instance_id)
            if widget:
                changed_ids.add(instance_id)
                widget.set_active(new_value)

        if changed_ids:
            self.active_changed.emit(changed_ids)

    def _on_selection_change(self, *_args):
        self.selection_changed.emit()

    def get_selected_items(self):
        instances = []
        context_selected = False
        for item in self.list_widget.selectedItems():
            instance_id = item.data(INSTANCE_ID_ROLE)
            if instance_id == CONTEXT_ID:
                context_selected = True
            else:
                widget = self._widgets_by_id.get(instance_id)
                if widget:
                    instances.append(widget.instance)

        return instances, context_selected

    def set_selected_items(self, instances, context_selected):
        indexes = []
        model = self.list_widget.model()
        if context_selected and self._context_item is not None:
            row = self.list_widget.row(self._context_item)
            index = model.index(row, 0)
            indexes.append(index)

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
