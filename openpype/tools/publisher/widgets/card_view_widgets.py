# -*- coding: utf-8 -*-
"""Card view instance with more information about each instance.

Instances are grouped under groups. Groups are defined by `creator_label`
attribute on instance (Group defined by creator).

Only one item can be selected at a time.

```
<i> : Icon. Can have Warning icon when context is not right
┌──────────────────────┐
│  Options             │
│ <Group 1> ────────── │
│ <i> <Instance 1>  [x]│
│ <i> <Instance 2>  [x]│
│ <Group 2> ────────── │
│ <i> <Instance 3>  [x]│
│ ...                  │
└──────────────────────┘
```
"""

import re
import collections

from Qt import QtWidgets, QtCore

from openpype.widgets.nice_checkbox import NiceCheckbox

from openpype.tools.utils import BaseClickableFrame
from .widgets import (
    AbstractInstanceView,
    ContextWarningLabel,
    IconValuePixmapLabel,
    PublishPixmapLabel
)
from ..constants import (
    CONTEXT_ID,
    CONTEXT_LABEL
)


class GroupWidget(QtWidgets.QWidget):
    """Widget wrapping instances under group."""
    selected = QtCore.Signal(str, str)
    active_changed = QtCore.Signal()
    removed_selected = QtCore.Signal()

    def __init__(self, group_name, group_icons, parent):
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
        self._group_icons = group_icons

        self._widgets_by_id = {}

        self._label_widget = label_widget
        self._content_layout = layout

    def get_widget_by_instance_id(self, instance_id):
        """Get instance widget by it's id."""
        return self._widgets_by_id.get(instance_id)

    def update_instance_values(self):
        """Trigger update on instance widgets."""
        for widget in self._widgets_by_id.values():
            widget.update_instance_values()

    def confirm_remove_instance_id(self, instance_id):
        """Delete widget by instance id."""
        widget = self._widgets_by_id.pop(instance_id)
        widget.setVisible(False)
        self._content_layout.removeWidget(widget)
        widget.deleteLater()

    def update_instances(self, instances):
        """Update instances for the group.

        Args:
            instances(list<CreatedInstance>): List of instances in
                CreateContext.
        """
        # Store instances by id and by subset name
        instances_by_id = {}
        instances_by_subset_name = collections.defaultdict(list)
        for instance in instances:
            instances_by_id[instance.id] = instance
            subset_name = instance["subset"]
            instances_by_subset_name[subset_name].append(instance)

        # Remove instance widgets that are not in passed instances
        for instance_id in tuple(self._widgets_by_id.keys()):
            if instance_id in instances_by_id:
                continue

            widget = self._widgets_by_id.pop(instance_id)
            if widget.is_selected:
                self.removed_selected.emit()

            widget.setVisible(False)
            self._content_layout.removeWidget(widget)
            widget.deleteLater()

        # Sort instances by subset name
        sorted_subset_names = list(sorted(instances_by_subset_name.keys()))
        # Add new instances to widget
        widget_idx = 1
        for subset_names in sorted_subset_names:
            for instance in instances_by_subset_name[subset_names]:
                if instance.id in self._widgets_by_id:
                    widget = self._widgets_by_id[instance.id]
                    widget.update_instance(instance)
                else:
                    group_icon = self._group_icons[instance.creator_identifier]
                    widget = InstanceCardWidget(
                        instance, group_icon, self
                    )
                    widget.selected.connect(self.selected)
                    widget.active_changed.connect(self.active_changed)
                    self._widgets_by_id[instance.id] = widget
                    self._content_layout.insertWidget(widget_idx, widget)
                widget_idx += 1


class CardWidget(BaseClickableFrame):
    """Clickable card used as bigger button."""
    selected = QtCore.Signal(str, str)
    # Group identifier of card
    # - this must be set because if send when mouse is released with card id
    _group_identifier = None

    def __init__(self, parent):
        super(CardWidget, self).__init__(parent)
        self.setObjectName("CardViewWidget")

        self._selected = False
        self._id = None

    @property
    def is_selected(self):
        """Is card selected."""
        return self._selected

    def set_selected(self, selected):
        """Set card as selected."""
        if selected == self._selected:
            return
        self._selected = selected
        state = "selected" if selected else ""
        self.setProperty("state", state)
        self.style().polish(self)

    def _mouse_release_callback(self):
        """Trigger selected signal."""
        self.selected.emit(self._id, self._group_identifier)


class ContextCardWidget(CardWidget):
    """Card for global context.

    Is not visually under group widget and is always at the top of card view.
    """
    def __init__(self, parent):
        super(ContextCardWidget, self).__init__(parent)

        self._id = CONTEXT_ID
        self._group_identifier = ""

        icon_widget = PublishPixmapLabel(None, self)
        icon_widget.setObjectName("FamilyIconLabel")

        label_widget = QtWidgets.QLabel(CONTEXT_LABEL, self)

        icon_layout = QtWidgets.QHBoxLayout()
        icon_layout.setContentsMargins(5, 5, 5, 5)
        icon_layout.addWidget(icon_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 10, 5)
        layout.addLayout(icon_layout, 0)
        layout.addWidget(label_widget, 1)

        self._icon_widget = icon_widget
        self._label_widget = label_widget


class InstanceCardWidget(CardWidget):
    """Card widget representing instance."""
    active_changed = QtCore.Signal()

    def __init__(self, instance, group_icon, parent):
        super(InstanceCardWidget, self).__init__(parent)

        self._id = instance.id
        self._group_identifier = instance.creator_label
        self._group_icon = group_icon

        self.instance = instance

        self._last_subset_name = None
        self._last_variant = None

        icon_widget = IconValuePixmapLabel(group_icon, self)
        icon_widget.setObjectName("FamilyIconLabel")
        context_warning = ContextWarningLabel(self)

        icon_layout = QtWidgets.QHBoxLayout()
        icon_layout.setContentsMargins(10, 5, 5, 5)
        icon_layout.addWidget(icon_widget)
        icon_layout.addWidget(context_warning)

        label_widget = QtWidgets.QLabel(self)
        active_checkbox = NiceCheckbox(parent=self)

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

        self._icon_widget = icon_widget
        self._label_widget = label_widget
        self._context_warning = context_warning
        self._active_checkbox = active_checkbox
        self._expand_btn = expand_btn

        self.update_instance_values()

    def set_active(self, new_value):
        """Set instance as active."""
        checkbox_value = self._active_checkbox.isChecked()
        instance_value = self.instance["active"]

        # First change instance value and them change checkbox
        # - prevent to trigger `active_changed` signal
        if instance_value != new_value:
            self.instance["active"] = new_value

        if checkbox_value != new_value:
            self._active_checkbox.setChecked(new_value)

    def update_instance(self, instance):
        """Update instance object and update UI."""
        self.instance = instance
        self.update_instance_values()

    def _validate_context(self):
        valid = self.instance.has_valid_context
        self._icon_widget.setVisible(valid)
        self._context_warning.setVisible(not valid)

    def _update_subset_name(self):
        variant = self.instance["variant"]
        subset_name = self.instance["subset"]
        if (
            variant == self._last_variant
            and subset_name == self._last_subset_name
        ):
            return

        self._last_variant = variant
        self._last_subset_name = subset_name
        # Make `variant` bold
        found_parts = set(re.findall(variant, subset_name, re.IGNORECASE))
        if found_parts:
            for part in found_parts:
                replacement = "<b>{}</b>".format(part)
                subset_name = subset_name.replace(part, replacement)

        self._label_widget.setText(subset_name)
        # HTML text will cause that label start catch mouse clicks
        # - disabling with changing interaction flag
        self._label_widget.setTextInteractionFlags(
            QtCore.Qt.NoTextInteraction
        )

    def update_instance_values(self):
        """Update instance data"""
        self._update_subset_name()
        self.set_active(self.instance["active"])
        self._validate_context()

    def _set_expanded(self, expanded=None):
        if expanded is None:
            expanded = not self.detail_widget.isVisible()
        self.detail_widget.setVisible(expanded)

    def _on_active_change(self):
        new_value = self._active_checkbox.isChecked()
        old_value = self.instance["active"]
        if new_value == old_value:
            return

        self.instance["active"] = new_value
        self.active_changed.emit()

    def _on_expend_clicked(self):
        self._set_expanded()


class InstanceCardView(AbstractInstanceView):
    """Publish access to card view.

    Wrapper of all widgets in card view.
    """
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
        """Modify sizeHint based on visibility of scroll bars."""
        # Calculate width hint by content widget and vertical scroll bar
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
        """Refresh instances in view based on CreatedContext."""
        # Create context item if is not already existing
        # - this must be as first thing to do as context item should be at the
        #   top
        if self._context_widget is None:
            widget = ContextCardWidget(self._content_widget)
            widget.selected.connect(self._on_widget_selection)

            self._context_widget = widget

            self.selection_changed.emit()
            self._content_layout.insertWidget(0, widget)

            self.select_item(CONTEXT_ID, None)

        # Prepare instances by group and identifiers by group
        instances_by_group = collections.defaultdict(list)
        identifiers_by_group = collections.defaultdict(set)
        for instance in self.controller.instances:
            group_name = instance.creator_label
            instances_by_group[group_name].append(instance)
            identifiers_by_group[group_name].add(
                instance.creator_identifier
            )

        # Remove groups that were not found in apassed instances
        for group_name in tuple(self._widgets_by_group.keys()):
            if group_name in instances_by_group:
                continue

            if group_name == self._selected_group:
                self._on_remove_selected()
            widget = self._widgets_by_group.pop(group_name)
            widget.setVisible(False)
            self._content_layout.removeWidget(widget)
            widget.deleteLater()

        # Sort groups
        sorted_group_names = list(sorted(instances_by_group.keys()))
        # Keep track of widget indexes
        # - we start with 1 because Context item as at the top
        widget_idx = 1
        for group_name in sorted_group_names:
            if group_name in self._widgets_by_group:
                group_widget = self._widgets_by_group[group_name]
            else:
                group_icons = {
                    idenfier: self.controller.get_icon_for_family(idenfier)
                    for idenfier in identifiers_by_group[group_name]
                }

                group_widget = GroupWidget(
                    group_name, group_icons, self._content_widget
                )
                group_widget.active_changed.connect(self._on_active_changed)
                group_widget.selected.connect(self._on_widget_selection)
                group_widget.removed_selected.connect(
                    self._on_remove_selected
                )
                self._content_layout.insertWidget(widget_idx, group_widget)
                self._widgets_by_group[group_name] = group_widget

            widget_idx += 1
            group_widget.update_instances(
                instances_by_group[group_name]
            )

    def refresh_instance_states(self):
        """Trigger update of instances on group widgets."""
        for widget in self._widgets_by_group.values():
            widget.update_instance_values()

    def _on_active_changed(self):
        self.active_changed.emit()

    def _on_widget_selection(self, instance_id, group_name):
        self.select_item(instance_id, group_name)

    def select_item(self, instance_id, group_name):
        """Select specific item by instance id.

        Pass `CONTEXT_ID` as instance id and empty string as group to select
        global context item.
        """
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
        """Get selected instance ids and context."""
        instances = []
        context_selected = False
        selected_widget = self._get_selected_widget()
        if selected_widget is self._context_widget:
            context_selected = True

        elif selected_widget is not None:
            instances.append(selected_widget.instance)

        return instances, context_selected
