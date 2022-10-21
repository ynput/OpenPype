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
from openpype.tools.utils.lib import html_escape
from .widgets import (
    AbstractInstanceView,
    ContextWarningLabel,
    IconValuePixmapLabel,
    PublishPixmapLabel
)
from ..constants import (
    CONTEXT_ID,
    CONTEXT_LABEL,
    CONTEXT_GROUP,
)


class SelectionType:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        if isinstance(other, SelectionType):
            other = other.name
        return self.name == other


class SelectionTypes:
    clear = SelectionType("clear")
    extend = SelectionType("extend")
    extend_to = SelectionType("extend_to")


class GroupWidget(QtWidgets.QWidget):
    """Widget wrapping instances under group."""

    selected = QtCore.Signal(str, str, SelectionType)
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
        self._ordered_instance_ids = []

        self._label_widget = label_widget
        self._content_layout = layout

    @property
    def group_name(self):
        """Group which widget represent.

        Returns:
            str: Name of group.
        """

        return self._group

    def get_selected_instance_ids(self):
        """Selected instance ids.

        Returns:
            Set[str]: Instance ids that are selected.
        """

        return {
            instance_id
            for instance_id, widget in self._widgets_by_id.items()
            if widget.is_selected
        }

    def get_selected_widgets(self):
        """Access to widgets marked as selected.

        Returns:
            List[InstanceCardWidget]: Instance widgets that are selected.
        """

        return [
            widget
            for instance_id, widget in self._widgets_by_id.items()
            if widget.is_selected
        ]

    def get_ordered_widgets(self):
        """Get instance ids in order as are shown in ui.

        Returns:
            List[str]: Instance ids.
        """

        return [
            self._widgets_by_id[instance_id]
            for instance_id in self._ordered_instance_ids
        ]

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
                    widget.selected.connect(self._on_widget_selection)
                    widget.active_changed.connect(self.active_changed)
                    self._widgets_by_id[instance.id] = widget
                    self._content_layout.insertWidget(widget_idx, widget)
                widget_idx += 1

        ordered_instance_ids = []
        for idx in range(self._content_layout.count()):
            if idx > 0:
                item = self._content_layout.itemAt(idx)
                widget = item.widget()
                if widget is not None:
                    ordered_instance_ids.append(widget.id)

        self._ordered_instance_ids = ordered_instance_ids

    def _on_widget_selection(self, instance_id, group_id, selection_type):
        self.selected.emit(instance_id, group_id, selection_type)


class CardWidget(BaseClickableFrame):
    """Clickable card used as bigger button."""

    selected = QtCore.Signal(str, str, SelectionType)
    # Group identifier of card
    # - this must be set because if send when mouse is released with card id
    _group_identifier = None

    def __init__(self, parent):
        super(CardWidget, self).__init__(parent)
        self.setObjectName("CardViewWidget")

        self._selected = False
        self._id = None

    @property
    def id(self):
        """Id of card."""

        return self._id

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

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        selection_type = SelectionTypes.clear
        if bool(modifiers & QtCore.Qt.ShiftModifier):
            selection_type = SelectionTypes.extend_to

        elif bool(modifiers & QtCore.Qt.ControlModifier):
            selection_type = SelectionTypes.extend

        self.selected.emit(self._id, self._group_identifier, selection_type)


class ContextCardWidget(CardWidget):
    """Card for global context.

    Is not visually under group widget and is always at the top of card view.
    """

    def __init__(self, parent):
        super(ContextCardWidget, self).__init__(parent)

        self._id = CONTEXT_ID
        self._group_identifier = CONTEXT_GROUP

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
        self._group_identifier = instance.group_label
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
        label = html_escape(self.instance.label)
        found_parts = set(re.findall(variant, label, re.IGNORECASE))
        if found_parts:
            for part in found_parts:
                replacement = "<b>{}</b>".format(part)
                label = label.replace(part, replacement)

        self._label_widget.setText(label)
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

        self._controller = controller

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

        self._context_widget = None
        self._widgets_by_group = {}
        self._ordered_groups = []

        self._explicitly_selected_instance_ids = []
        self._explicitly_selected_groups = []

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

    def _get_selected_widgets(self):
        output = []
        if (
            self._context_widget is not None
            and self._context_widget.is_selected
        ):
            output.append(self._context_widget)

        for group_widget in self._widgets_by_group.values():
            for widget in group_widget.get_selected_widgets():
                output.append(widget)
        return output

    def _get_selected_instance_ids(self):
        output = []
        if (
            self._context_widget is not None
            and self._context_widget.is_selected
        ):
            output.append(CONTEXT_ID)

        for group_widget in self._widgets_by_group.values():
            output.extend(group_widget.get_selected_instance_ids())
        return output

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

        # Prepare instances by group and identifiers by group
        instances_by_group = collections.defaultdict(list)
        identifiers_by_group = collections.defaultdict(set)
        for instance in self._controller.instances.values():
            group_name = instance.group_label
            instances_by_group[group_name].append(instance)
            identifiers_by_group[group_name].add(
                instance.creator_identifier
            )

        # Remove groups that were not found in apassed instances
        for group_name in tuple(self._widgets_by_group.keys()):
            if group_name in instances_by_group:
                continue

            widget = self._widgets_by_group.pop(group_name)
            widget.setVisible(False)
            self._content_layout.removeWidget(widget)
            widget.deleteLater()

            if group_name in self._explicitly_selected_groups:
                self._explicitly_selected_groups.remove(group_name)

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
                    idenfier: self._controller.get_creator_icon(idenfier)
                    for idenfier in identifiers_by_group[group_name]
                }

                group_widget = GroupWidget(
                    group_name, group_icons, self._content_widget
                )
                group_widget.active_changed.connect(self._on_active_changed)
                group_widget.selected.connect(self._on_widget_selection)
                self._content_layout.insertWidget(widget_idx, group_widget)
                self._widgets_by_group[group_name] = group_widget

            widget_idx += 1
            group_widget.update_instances(
                instances_by_group[group_name]
            )

        ordered_group_names = [CONTEXT_GROUP]
        for idx in range(self._content_layout.count()):
            if idx > 0:
                item = self._content_layout.itemAt(idx)
                group_widget = item.widget()
                if group_widget is not None:
                    ordered_group_names.append(group_widget.group_name)

        self._ordered_groups = ordered_group_names

    def refresh_instance_states(self):
        """Trigger update of instances on group widgets."""
        for widget in self._widgets_by_group.values():
            widget.update_instance_values()

    def _on_active_changed(self):
        self.active_changed.emit()

    def _on_widget_selection(self, instance_id, group_name, selection_type):
        """Select specific item by instance id.

        Pass `CONTEXT_ID` as instance id and empty string as group to select
        global context item.
        """
        if instance_id == CONTEXT_ID:
            new_widget = self._context_widget
        else:
            group_widget = self._widgets_by_group[group_name]
            new_widget = group_widget.get_widget_by_instance_id(instance_id)

        if selection_type is SelectionTypes.clear:
            self._select_item_clear(instance_id, group_name, new_widget)
        elif selection_type is SelectionTypes.extend:
            self._select_item_extend(instance_id, group_name, new_widget)
        elif selection_type is SelectionTypes.extend_to:
            self._select_item_extend_to(instance_id, group_name, new_widget)

        self.selection_changed.emit()

    def _select_item_clear(self, instance_id, group_name, new_widget):
        """Select specific item by instance id and clear previous selection.

        Pass `CONTEXT_ID` as instance id and empty string as group to select
        global context item.
        """

        selected_widgets = self._get_selected_widgets()
        for widget in selected_widgets:
            if widget.id != instance_id:
                widget.set_selected(False)

        self._explicitly_selected_groups = [group_name]
        self._explicitly_selected_instance_ids = [instance_id]

        if new_widget is not None:
            new_widget.set_selected(True)

    def _select_item_extend(self, instance_id, group_name, new_widget):
        """Add/Remove single item to/from current selection.

        If item is already selected the selection is removed.
        """

        self._explicitly_selected_instance_ids = (
            self._get_selected_instance_ids()
        )
        if new_widget.is_selected:
            self._explicitly_selected_instance_ids.remove(instance_id)
            new_widget.set_selected(False)
            remove_group = False
            if instance_id == CONTEXT_ID:
                remove_group = True
            else:
                group_widget = self._widgets_by_group[group_name]
                if not group_widget.get_selected_widgets():
                    remove_group = True

            if remove_group:
                self._explicitly_selected_groups.remove(group_name)
            return

        self._explicitly_selected_instance_ids.append(instance_id)
        if group_name in self._explicitly_selected_groups:
            self._explicitly_selected_groups.remove(group_name)
        self._explicitly_selected_groups.append(group_name)
        new_widget.set_selected(True)

    def _select_item_extend_to(self, instance_id, group_name, new_widget):
        """Extend selected items to specific instance id.

        This method is handling Shift+click selection of widgets. Selection
        is not stored to explicit selection items. That's because user can
        shift select again and it should use last explicit selected item as
        source item for selection.

        Items selected via this function can get to explicit selection only if
        selection is extended by one specific item ('_select_item_extend').
        From that moment the selection is locked to new last explicit selected
        item.

        It's required to traverse through group widgets in their UI order and
        through their instances in UI order. All explicitly selected items
        must not change their selection state during this function. Passed
        instance id can be above or under last selected item so a start item
        and end item must be found to be able know which direction is selection
        happening.
        """

        # Start group name (in '_ordered_groups')
        start_group = None
        # End group name (in '_ordered_groups')
        end_group = None
        # Instance id of first selected item
        start_instance_id = None
        # Instance id of last selected item
        end_instance_id = None

        # Get previously selected group by explicit selected groups
        previous_group = None
        if self._explicitly_selected_groups:
            previous_group = self._explicitly_selected_groups[-1]

        # Find last explicitly selected instance id
        previous_last_selected_id = None
        if self._explicitly_selected_instance_ids:
            previous_last_selected_id = (
                self._explicitly_selected_instance_ids[-1]
            )

        # If last instance id was not found or available then last selected
        #   group is also invalid.
        # NOTE: This probably never happen?
        if previous_last_selected_id is None:
            previous_group = None

        # Check if previously selected group is available and find out if
        #   new instance group is above or under previous selection
        # - based on these information are start/end group/instance filled
        if previous_group in self._ordered_groups:
            new_idx = self._ordered_groups.index(group_name)
            prev_idx = self._ordered_groups.index(previous_group)
            if new_idx < prev_idx:
                start_group = group_name
                end_group = previous_group
                start_instance_id = instance_id
                end_instance_id = previous_last_selected_id
            else:
                start_group = previous_group
                end_group = group_name
                start_instance_id = previous_last_selected_id
                end_instance_id = instance_id

        # If start group is not set then use context item group name
        if start_group is None:
            start_group = CONTEXT_GROUP

        # If start instance id is not filled then use context id (similar to
        #   group)
        if start_instance_id is None:
            start_instance_id = CONTEXT_ID

        # If end group is not defined then use passed group name
        #   - this can be happen when previous group was not selected
        #   - when this happens the selection will probably happen from context
        #       item to item selected by user
        if end_group is None:
            end_group = group_name

        # If end instance is not filled then use instance selected by user
        if end_instance_id is None:
            end_instance_id = instance_id

        # Start and end group are the same
        # - a different logic is needed in that case
        same_group = start_group == end_group

        # Process known information and change selection of items
        passed_start_group = False
        passed_end_group = False
        # Go through ordered groups (from top to bottom) and change selection
        for name in self._ordered_groups:
            # Prepare sorted instance widgets
            if name == CONTEXT_GROUP:
                sorted_widgets = [self._context_widget]
            else:
                group_widget = self._widgets_by_group[name]
                sorted_widgets = group_widget.get_ordered_widgets()

            # Change selection based on explicit selection if start group
            #   was not passed yet
            if not passed_start_group:
                if name != start_group:
                    for widget in sorted_widgets:
                        widget.set_selected(
                            widget.id in self._explicitly_selected_instance_ids
                        )
                    continue

            # Change selection based on explicit selection if end group
            #   already passed
            if passed_end_group:
                for widget in sorted_widgets:
                    widget.set_selected(
                        widget.id in self._explicitly_selected_instance_ids
                    )
                continue

            # Start group is already passed and end group was not yet hit
            if same_group:
                passed_start_group = True
                passed_end_group = True
                passed_start_instance = False
                passed_end_instance = False
                for widget in sorted_widgets:
                    if not passed_start_instance:
                        if widget.id in (start_instance_id, end_instance_id):
                            if widget.id != start_instance_id:
                                # Swap start/end instance if start instance is
                                #   after end
                                # - fix 'passed_end_instance' check
                                start_instance_id, end_instance_id = (
                                    end_instance_id, start_instance_id
                                )
                            passed_start_instance = True

                    # Find out if widget should be selected
                    select = False
                    if passed_end_instance:
                        select = False

                    elif passed_start_instance:
                        select = True

                    # Check if instance is in explicitly selected items if
                    #   should ont be selected
                    if (
                        not select
                        and widget.id in self._explicitly_selected_instance_ids
                    ):
                        select = True

                    widget.set_selected(select)

                    if (
                        not passed_end_instance
                        and widget.id == end_instance_id
                    ):
                        passed_end_instance = True

            elif name == start_group:
                # First group from which selection should start
                # - look for start instance first from which the selection
                #   should happen
                passed_start_group = True
                passed_start_instance = False
                for widget in sorted_widgets:
                    if widget.id == start_instance_id:
                        passed_start_instance = True

                    select = False
                    # Check if passed start instance or instance is
                    #   in explicitly selected items to be selected
                    if (
                        passed_start_instance
                        or widget.id in self._explicitly_selected_instance_ids
                    ):
                        select = True
                    widget.set_selected(select)

            elif name == end_group:
                # Last group where selection should happen
                # - look for end instance first after which the selection
                #   should stop
                passed_end_group = True
                passed_end_instance = False
                for widget in sorted_widgets:
                    select = False
                    # Check if not yet passed end instance or if instance is
                    #   in explicitly selected items to be selected
                    if (
                        not passed_end_instance
                        or widget.id in self._explicitly_selected_instance_ids
                    ):
                        select = True

                    widget.set_selected(select)

                    if widget.id == end_instance_id:
                        passed_end_instance = True

            else:
                # Just select everything between start and end group
                for widget in sorted_widgets:
                    widget.set_selected(True)

    def get_selected_items(self):
        """Get selected instance ids and context."""
        instances = []
        selected_widgets = self._get_selected_widgets()

        context_selected = False
        for widget in selected_widgets:
            if widget is self._context_widget:
                context_selected = True
            else:
                instances.append(widget.id)

        return instances, context_selected

    def set_selected_items(self, instance_ids, context_selected):
        s_instance_ids = set(instance_ids)
        cur_ids, cur_context = self.get_selected_items()
        if (
            set(cur_ids) == s_instance_ids
            and cur_context == context_selected
        ):
            return

        selected_groups = []
        selected_instances = []
        if context_selected:
            selected_groups.append(CONTEXT_GROUP)
            selected_instances.append(CONTEXT_ID)

        self._context_widget.set_selected(context_selected)

        for group_name in self._ordered_groups:
            if group_name == CONTEXT_GROUP:
                continue

            group_widget = self._widgets_by_group[group_name]
            group_selected = False
            for widget in group_widget.get_ordered_widgets():
                select = False
                if widget.id in s_instance_ids:
                    selected_instances.append(widget.id)
                    group_selected = True
                    select = True
                widget.set_selected(select)

            if group_selected:
                selected_groups.append(group_name)

        self._explicitly_selected_groups = selected_groups
        self._explicitly_selected_instance_ids = selected_instances
