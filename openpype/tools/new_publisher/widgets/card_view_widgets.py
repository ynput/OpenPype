import re
import collections

from Qt import QtWidgets, QtCore

from openpype.widgets.nice_checkbox import NiceCheckbox

from .widgets import (
    AbstractInstanceView,
    ContextWarningLabel,
    ClickableFrame,
    IconValuePixmapLabel,
    TransparentPixmapLabel
)
from ..constants import (
    CONTEXT_ID,
    CONTEXT_LABEL
)


class GroupWidget(QtWidgets.QWidget):
    selected = QtCore.Signal(str, str)
    active_changed = QtCore.Signal()
    removed_selected = QtCore.Signal()

    def __init__(self, group_name, group_icon, parent):
        super(GroupWidget, self).__init__(parent)

        label_widget = QtWidgets.QLabel(group_name, self)

        line_widget = QtWidgets.QWidget(self)
        line_widget.setObjectName("Separator")
        line_widget.setMinimumHeight(2)
        line_widget.setMaximumHeight(2)

        label_layout = QtWidgets.QHBoxLayout()
        label_layout.setAlignment(QtCore.Qt.AlignVCenter)
        label_layout.setSpacing(10)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.addWidget(label_widget, 0)
        label_layout.addWidget(line_widget, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(label_layout, 0)

        self._group = group_name
        self._group_icon = group_icon

        self._widgets_by_id = {}

        self._label_widget = label_widget
        self._content_layout = layout

    def get_widget_by_instance_id(self, instance_id):
        return self._widgets_by_id.get(instance_id)

    def update_instance_values(self):
        for widget in self._widgets_by_id.values():
            widget.update_instance_values()

    def confirm_remove_instance_id(self, instance_id):
        widget = self._widgets_by_id.pop(instance_id)
        widget.setVisible(False)
        self._content_layout.removeWidget(widget)
        widget.deleteLater()

    def update_instances(self, instances):
        instances_by_id = {}
        instances_by_subset_name = collections.defaultdict(list)
        for instance in instances:
            instances_by_id[instance.id] = instance
            subset_name = instance.data["subset"]
            instances_by_subset_name[subset_name].append(instance)

        for instance_id in tuple(self._widgets_by_id.keys()):
            if instance_id in instances_by_id:
                continue

            widget = self._widgets_by_id.pop(instance_id)
            if widget.is_selected:
                self.removed_selected.emit()

            widget.setVisible(False)
            self._content_layout.removeWidget(widget)
            widget.deleteLater()

        sorted_subset_names = list(sorted(instances_by_subset_name.keys()))
        widget_idx = 1
        for subset_names in sorted_subset_names:
            for instance in instances_by_subset_name[subset_names]:
                if instance.id in self._widgets_by_id:
                    widget = self._widgets_by_id[instance.id]
                    widget.update_instance(instance)
                else:
                    widget = InstanceCardWidget(
                        instance, self._group_icon, self
                    )
                    widget.selected.connect(self.selected)
                    widget.active_changed.connect(self.active_changed)
                    self._widgets_by_id[instance.id] = widget
                    self._content_layout.insertWidget(widget_idx, widget)
                widget_idx += 1


class CardWidget(ClickableFrame):
    selected = QtCore.Signal(str, str)
    # This must be set
    _group_identifier = None

    def __init__(self, parent):
        super(CardWidget, self).__init__(parent)
        self.setObjectName("CardViewWidget")

        self._selected = False
        self._id = None

    @property
    def is_selected(self):
        return self._selected

    def set_selected(self, selected):
        if selected == self._selected:
            return
        self._selected = selected
        state = "selected" if selected else ""
        self.setProperty("state", state)
        self.style().polish(self)

    def _mouse_release_callback(self):
        self.selected.emit(self._id, self._group_identifier)


class ContextCardWidget(CardWidget):
    def __init__(self, parent):
        super(ContextCardWidget, self).__init__(parent)

        self._id = CONTEXT_ID
        self._group_identifier = ""

        icon_widget = TransparentPixmapLabel(self)
        icon_widget.setObjectName("FamilyIconLabel")

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
    active_changed = QtCore.Signal()

    def __init__(self, instance, group_icon, parent):
        super(InstanceCardWidget, self).__init__(parent)

        self._id = instance.id
        self._group_identifier = instance.creator_identifier
        self._group_icon = group_icon

        self.instance = instance

        icon_widget = IconValuePixmapLabel(group_icon, self)
        icon_widget.setObjectName("FamilyIconLabel")
        context_warning = ContextWarningLabel(self)

        icon_layout = QtWidgets.QHBoxLayout()
        icon_layout.setContentsMargins(10, 5, 5, 5)
        icon_layout.addWidget(icon_widget)
        icon_layout.addWidget(context_warning)

        variant = instance.data["variant"]
        subset_name = instance.data["subset"]
        found_parts = set(re.findall(variant, subset_name, re.IGNORECASE))
        if found_parts:
            for part in found_parts:
                replacement = "<b>{}</b>".format(part)
                subset_name = subset_name.replace(part, replacement)

        label_widget = QtWidgets.QLabel(subset_name, self)
        # HTML text will cause that label start catch mouse clicks
        # - disabling with changing interaction flag
        label_widget.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)

        active_checkbox = NiceCheckbox(parent=self)
        active_checkbox.setChecked(instance.data["active"])

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

        self._validate_context()

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

    def _validate_context(self):
        valid = self.instance.has_valid_context
        self.icon_widget.setVisible(valid)
        self.context_warning.setVisible(not valid)

    def update_instance_values(self):
        self.set_active(self.instance.data["active"])
        self._validate_context()

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
        self.active_changed.emit()

    def _on_expend_clicked(self):
        self._set_expanded()


class InstanceCardView(AbstractInstanceView):
    def __init__(self, controller, parent):
        super(InstanceCardView, self).__init__(parent)

        self.controller = controller

        scroll_area = QtWidgets.QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollbar_bg = scroll_area.verticalScrollBar().parent()
        if scrollbar_bg:
            scrollbar_bg.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        scroll_area.setViewportMargins(0, 0, 0, 0)

        content_widget = QtWidgets.QWidget(scroll_area)

        scroll_area.setWidget(content_widget)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area)

        self._scroll_area = scroll_area
        self._content_layout = content_layout
        self._content_widget = content_widget

        self._widgets_by_group = {}
        self._context_widget = None

        self._selected_group = None
        self._selected_instance_id = None

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            self.sizePolicy().verticalPolicy()
        )

    def sizeHint(self):
        # Calculate width hint by content widget and verticall scroll bar
        scroll_bar = self._scroll_area.verticalScrollBar()
        width = (
            self._content_widget.sizeHint().width()
            + scroll_bar.sizeHint().width()
        )

        result = super(InstanceCardView, self).sizeHint()
        result.setWidth(width)
        return result

    def _get_selected_widget(self):
        if self._selected_instance_id == CONTEXT_ID:
            return self._context_widget

        group_widget = self._widgets_by_group.get(
            self._selected_group
        )
        if group_widget is not None:
            widget = group_widget.get_widget_by_instance_id(
                self._selected_instance_id
            )
            if widget is not None:
                return widget

        return None

    def refresh(self):
        if self._context_widget is None:
            widget = ContextCardWidget(self._content_widget)
            widget.selected.connect(self._on_widget_selection)

            self._context_widget = widget

            self.selection_changed.emit()
            self._content_layout.insertWidget(0, widget)

            self.select_item(CONTEXT_ID, None)

        instances_by_creator = collections.defaultdict(list)
        for instance in self.controller.instances:
            identifier = instance.creator_identifier
            instances_by_creator[identifier].append(instance)

        for identifier in tuple(self._widgets_by_group.keys()):
            if identifier in instances_by_creator:
                continue

            if identifier == self._selected_group:
                self._on_remove_selected()
            widget = self._widgets_by_group.pop(identifier)
            widget.setVisible(False)
            self._content_layout.removeWidget(widget)
            widget.deleteLater()

        sorted_identifiers = list(sorted(instances_by_creator.keys()))
        widget_idx = 1
        for creator_identifier in sorted_identifiers:
            if creator_identifier in self._widgets_by_group:
                group_widget = self._widgets_by_group[creator_identifier]
            else:
                group_icon = self.controller.get_icon_for_family(
                    creator_identifier
                )
                group_widget = GroupWidget(
                    creator_identifier, group_icon, self._content_widget
                )
                group_widget.active_changed.connect(self._on_active_changed)
                group_widget.selected.connect(self._on_widget_selection)
                group_widget.removed_selected.connect(
                    self._on_remove_selected
                )
                self._content_layout.insertWidget(widget_idx, group_widget)
                self._widgets_by_group[creator_identifier] = group_widget

            widget_idx += 1
            group_widget.update_instances(
                instances_by_creator[creator_identifier]
            )

    def refresh_instance_states(self):
        for widget in self._widgets_by_group.values():
            widget.update_instance_values()

    def _on_active_changed(self):
        self.active_changed.emit()

    def _on_widget_selection(self, instance_id, group_name):
        self.select_item(instance_id, group_name)

    def select_item(self, instance_id, group_name):
        if instance_id == CONTEXT_ID:
            new_widget = self._context_widget
        else:
            group_widget = self._widgets_by_group[group_name]
            new_widget = group_widget.get_widget_by_instance_id(instance_id)

        selected_widget = self._get_selected_widget()
        if new_widget is selected_widget:
            return

        if selected_widget is not None:
            selected_widget.set_selected(False)

        self._selected_instance_id = instance_id
        self._selected_group = group_name
        if new_widget is not None:
            new_widget.set_selected(True)

        self.selection_changed.emit()

    def _on_remove_selected(self):
        selected_widget = self._get_selected_widget()
        if selected_widget is None:
            self._on_widget_selection(CONTEXT_ID, None)

    def get_selected_items(self):
        instances = []
        context_selected = False
        selected_widget = self._get_selected_widget()
        if selected_widget is self._context_widget:
            context_selected = True

        elif selected_widget is not None:
            instances.append(selected_widget.instance)

        return instances, context_selected
