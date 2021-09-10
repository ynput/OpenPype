from Qt import QtWidgets, QtCore

from openpype.widgets.nice_checkbox import NiceCheckbox

from .widgets import (
    AbstractInstanceView,
    ContextWarningLabel,
    ClickableFrame
)
from ..constants import (
    INSTANCE_ID_ROLE,
    CONTEXT_ID,
    CONTEXT_LABEL
)


class FamilyLabel(QtWidgets.QWidget):
    def __init__(self, family, parent):
        super(FamilyLabel, self).__init__(parent)

        label_widget = QtWidgets.QLabel(family, self)

        line_widget = QtWidgets.QWidget(self)
        line_widget.setObjectName("Separator")
        line_widget.setMinimumHeight(1)
        line_widget.setMaximumHeight(1)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label_widget, 0)
        layout.addWidget(line_widget, 1)

        self._label_widget = label_widget


class CardWidget(ClickableFrame):
    selected = QtCore.Signal(str)

    def __init__(self, parent):
        super(CardWidget, self).__init__(parent)
        self.setObjectName("CardViewWidget")

        self._selected = False
        self._id = None

    def set_selected(self, selected):
        if selected == self._selected:
            return
        self._selected = selected
        state = "selected" if selected else ""
        self.setProperty("state", state)
        self.style().polish(self)

    def _mouse_release_callback(self):
        self.selected.emit(self._id)


class ContextCardWidget(CardWidget):
    def __init__(self, parent):
        super(ContextCardWidget, self).__init__(parent)

        self._id = CONTEXT_ID

        icon_widget = QtWidgets.QLabel(self)

        label_widget = QtWidgets.QLabel(CONTEXT_LABEL, self)

        icon_layout = QtWidgets.QHBoxLayout()
        icon_layout.setContentsMargins(5, 5, 5, 5)
        icon_layout.addWidget(icon_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 10, 5)
        layout.addLayout(icon_layout, 0)
        layout.addWidget(label_widget, 1)

        self.icon_widget = icon_widget
        self.label_widget = label_widget


class InstanceCardWidget(CardWidget):
    active_changed = QtCore.Signal(str, bool)

    def __init__(self, instance, parent):
        super(InstanceCardWidget, self).__init__(parent)

        self._id = instance.data["uuid"]

        self.instance = instance

        icon_widget = QtWidgets.QLabel(self)

        icon_layout = QtWidgets.QHBoxLayout()
        icon_layout.setContentsMargins(5, 5, 5, 5)
        icon_layout.addWidget(icon_widget)

        label_widget = QtWidgets.QLabel(instance.data["subset"], self)

        active_checkbox = NiceCheckbox(parent=self)
        active_checkbox.setChecked(instance.data["active"])

        context_warning = ContextWarningLabel(self)
        if instance.has_valid_context:
            context_warning.setVisible(False)

        expand_btn = QtWidgets.QToolButton(self)
        # Not yet implemented
        expand_btn.setVisible(False)
        expand_btn.setObjectName("ArrowBtn")
        expand_btn.setArrowType(QtCore.Qt.DownArrow)
        expand_btn.setMaximumWidth(14)
        expand_btn.setEnabled(False)

        detail_widget = QtWidgets.QWidget(self)
        detail_widget.setVisible(False)
        self.detail_widget = detail_widget

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addLayout(icon_layout, 0)
        top_layout.addWidget(label_widget, 1)
        top_layout.addWidget(context_warning, 0)
        top_layout.addWidget(active_checkbox, 0)
        top_layout.addWidget(expand_btn, 0)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 10, 5)
        layout.addLayout(top_layout)
        layout.addWidget(detail_widget)

        active_checkbox.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        expand_btn.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        active_checkbox.stateChanged.connect(self._on_active_change)
        expand_btn.clicked.connect(self._on_expend_clicked)

        self.icon_widget = icon_widget
        self.label_widget = label_widget
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

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)

        self._content_layout = layout

        self._widgets_by_id = {}
        self._family_widgets_by_name = {}
        self._context_widget = None

        self._selected_widget = None

    def refresh(self):
        instances_by_id = {}
        for instance in self.controller.instances:
            instance_id = instance.data["uuid"]
            instances_by_id[instance_id] = instance

        if not self._context_widget:
            widget = ContextCardWidget(self)
            widget.selected.connect(self._on_widget_selection)
            widget.set_selected(True)
            self.selection_changed.emit()
            self._content_layout.insertWidget(0, widget)
            self._context_widget = widget
            self._selected_widget = widget

        for instance_id in tuple(self._widgets_by_id.keys()):
            if instance_id not in instances_by_id:
                widget = self._widgets_by_id.pop(instance_id)
                widget.setVisible(False)
                self._content_widget.removeWidget(widget)
                widget.deleteLater()

        for instance_id, instance in instances_by_id.items():
            if instance_id in self._widgets_by_id:
                widget = self._widgets_by_id[instance_id]
                widget.update_instance(instance)
                continue

            family = instance.data["family"]
            if family not in self._family_widgets_by_name:
                widget = FamilyLabel(family, self)
                self._family_widgets_by_name[family] = widget
                pos = self._content_layout.count() - 1
                self._content_layout.insertWidget(pos, widget)

            widget = InstanceCardWidget(instance, self)
            widget.selected.connect(self._on_widget_selection)
            widget.active_changed.connect(self._on_active_changed)
            self._widgets_by_id[instance_id] = widget
            pos = self._content_layout.count() - 1
            self._content_layout.insertWidget(pos, widget)

    def refresh_instance_states(self):
        for widget in self._widgets_by_id.values():
            widget.update_instance_values()

    def _on_active_changed(self):
        self.active_changed.emit()

    def _on_widget_selection(self, widget_id):
        if widget_id == CONTEXT_ID:
            new_widget = self._context_widget
        else:
            new_widget = self._widgets_by_id.get(widget_id)

        if new_widget is self._selected_widget:
            return

        if self._selected_widget is not None:
            self._selected_widget.set_selected(False)

        self._selected_widget = new_widget
        if new_widget is not None:
            new_widget.set_selected(True)

        self.selection_changed.emit()

    def get_selected_items(self):
        instances = []
        context_selected = False
        if self._selected_widget is self._context_widget:
            context_selected = True

        elif self._selected_widget is not None:
            instances.append(self._selected_widget.instance)

        return instances, context_selected

    def set_selected_items(self, instances, context_selected):
        pass
