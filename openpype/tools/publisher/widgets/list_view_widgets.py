"""Simple easy instance view grouping instances into collapsible groups.

View has multiselection ability. Groups are defined by `creator_label`
attribute on instance (Group defined by creator).

Each item can be enabled/disabled with their checkbox, whole group
can be enabled/disabled with checkbox on group or
selection can be enabled disabled using checkbox or keyboard key presses:
- Space - change state of selection to opposite
- Enter - enable selection
- Backspace - disable selection

```
|- Options
|- <Group 1> [x]
|  |- <Instance 1> [x]
|  |- <Instance 2> [x]
|  ...
|- <Group 2> [ ]
|  |- <Instance 3> [ ]
|  ...
...
```
"""
import collections

from Qt import QtWidgets, QtCore, QtGui

from openpype.style import get_objected_colors
from openpype.widgets.nice_checkbox import NiceCheckbox
from .widgets import AbstractInstanceView
from ..constants import (
    INSTANCE_ID_ROLE,
    SORT_VALUE_ROLE,
    IS_GROUP_ROLE,
    CONTEXT_ID,
    CONTEXT_LABEL
)


class ListItemDelegate(QtWidgets.QStyledItemDelegate):
    """Generic delegate for instance group.

    All indexes having `IS_GROUP_ROLE` data set to True will use
    `group_item_paint` method to draw it's content otherwise default styled
    item delegate paint method is used.

    Goal is to draw group items with different colors for normal, hover and
    pressed state.
    """
    radius_ratio = 0.3

    def __init__(self, parent):
        super(ListItemDelegate, self).__init__(parent)

        colors_data = get_objected_colors()
        group_color_info = colors_data["publisher"]["list-view-group"]

        self._group_colors = {
            key: value.get_qcolor()
            for key, value in group_color_info.items()
        }

    def paint(self, painter, option, index):
        if index.data(IS_GROUP_ROLE):
            self.group_item_paint(painter, option, index)
        else:
            super(ListItemDelegate, self).paint(painter, option, index)

    def group_item_paint(self, painter, option, index):
        """Paint group item."""
        self.initStyleOption(option, index)

        bg_rect = QtCore.QRectF(
            option.rect.left(), option.rect.top() + 1,
            option.rect.width(), option.rect.height() - 2
        )
        ratio = bg_rect.height() * self.radius_ratio
        bg_path = QtGui.QPainterPath()
        bg_path.addRoundedRect(
            QtCore.QRectF(bg_rect), ratio, ratio
        )

        painter.save()
        painter.setRenderHints(
            painter.Antialiasing
            | painter.SmoothPixmapTransform
            | painter.TextAntialiasing
        )

        # Draw backgrounds
        painter.fillPath(bg_path, self._group_colors["bg"])
        selected = option.state & QtWidgets.QStyle.State_Selected
        hovered = option.state & QtWidgets.QStyle.State_MouseOver
        if selected and hovered:
            painter.fillPath(bg_path, self._group_colors["bg-selected-hover"])

        elif hovered:
            painter.fillPath(bg_path, self._group_colors["bg-hover"])

        painter.restore()


class InstanceListItemWidget(QtWidgets.QWidget):
    """Widget with instance info drawn over delegate paint.

    This is required to be able use custom checkbox on custom place.
    """
    active_changed = QtCore.Signal(str, bool)

    def __init__(self, instance, parent):
        super(InstanceListItemWidget, self).__init__(parent)

        self.instance = instance

        subset_name_label = QtWidgets.QLabel(instance["subset"], self)
        subset_name_label.setObjectName("ListViewSubsetName")

        active_checkbox = NiceCheckbox(parent=self)
        active_checkbox.setChecked(instance["active"])

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

        self._subset_name_label = subset_name_label
        self._active_checkbox = active_checkbox

        self._has_valid_context = None

        self._set_valid_property(instance.has_valid_context)

    def _set_valid_property(self, valid):
        if self._has_valid_context == valid:
            return
        self._has_valid_context = valid
        state = ""
        if not valid:
            state = "invalid"
        self._subset_name_label.setProperty("state", state)
        self._subset_name_label.style().polish(self._subset_name_label)

    def is_active(self):
        """Instance is activated."""
        return self.instance["active"]

    def set_active(self, new_value):
        """Change active state of instance and checkbox."""
        checkbox_value = self._active_checkbox.isChecked()
        instance_value = self.instance["active"]
        if new_value is None:
            new_value = not instance_value

        # First change instance value and them change checkbox
        # - prevent to trigger `active_changed` signal
        if instance_value != new_value:
            self.instance["active"] = new_value

        if checkbox_value != new_value:
            self._active_checkbox.setChecked(new_value)

    def update_instance(self, instance):
        """Update instance object."""
        self.instance = instance
        self.update_instance_values()

    def update_instance_values(self):
        """Update instance data propagated to widgets."""
        # Check subset name
        subset_name = self.instance["subset"]
        if subset_name != self._subset_name_label.text():
            self._subset_name_label.setText(subset_name)
        # Check active state
        self.set_active(self.instance["active"])
        # Check valid states
        self._set_valid_property(self.instance.has_valid_context)

    def _on_active_change(self):
        new_value = self._active_checkbox.isChecked()
        old_value = self.instance["active"]
        if new_value == old_value:
            return

        self.instance["active"] = new_value
        self.active_changed.emit(self.instance.id, new_value)


class ListContextWidget(QtWidgets.QFrame):
    """Context (or global attributes) widget."""
    def __init__(self, parent):
        super(ListContextWidget, self).__init__(parent)

        label_widget = QtWidgets.QLabel(CONTEXT_LABEL, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 2, 0)
        layout.addWidget(
            label_widget, 1, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.label_widget = label_widget


class InstanceListGroupWidget(QtWidgets.QFrame):
    """Widget representing group of instances.

    Has collapse/expand indicator, label of group and checkbox modifying all of
    it's children.
    """
    expand_changed = QtCore.Signal(str, bool)
    toggle_requested = QtCore.Signal(str, int)

    def __init__(self, group_name, parent):
        super(InstanceListGroupWidget, self).__init__(parent)
        self.setObjectName("InstanceListGroupWidget")

        self.group_name = group_name
        self._expanded = False

        expand_btn = QtWidgets.QToolButton(self)
        expand_btn.setObjectName("ArrowBtn")
        expand_btn.setArrowType(QtCore.Qt.RightArrow)
        expand_btn.setMaximumWidth(14)

        name_label = QtWidgets.QLabel(group_name, self)

        toggle_checkbox = NiceCheckbox(parent=self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 2, 0)
        layout.addWidget(expand_btn)
        layout.addWidget(
            name_label, 1, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        layout.addWidget(toggle_checkbox, 0)

        name_label.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        expand_btn.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        expand_btn.clicked.connect(self._on_expand_clicked)
        toggle_checkbox.stateChanged.connect(self._on_checkbox_change)

        self._ignore_state_change = False

        self._expected_checkstate = None

        self.name_label = name_label
        self.expand_btn = expand_btn
        self.toggle_checkbox = toggle_checkbox

    def set_checkstate(self, state):
        """Change checkstate of "active" checkbox.

        Args:
            state(QtCore.Qt.CheckState): Checkstate of checkbox. Have 3
                variants Unchecked, Checked and PartiallyChecked.
        """
        if self.checkstate() == state:
            return
        self._ignore_state_change = True
        self.toggle_checkbox.setCheckState(state)
        self._ignore_state_change = False

    def checkstate(self):
        """CUrrent checkstate of "active" checkbox."""
        return self.toggle_checkbox.checkState()

    def _on_checkbox_change(self, state):
        if not self._ignore_state_change:
            self.toggle_requested.emit(self.group_name, state)

    def _on_expand_clicked(self):
        self.expand_changed.emit(self.group_name, not self._expanded)

    def set_expanded(self, expanded):
        """Change icon of collapse/expand identifier."""
        if self._expanded == expanded:
            return

        self._expanded = expanded
        if expanded:
            self.expand_btn.setArrowType(QtCore.Qt.DownArrow)
        else:
            self.expand_btn.setArrowType(QtCore.Qt.RightArrow)


class InstanceTreeView(QtWidgets.QTreeView):
    """View showing instances and their groups."""
    toggle_requested = QtCore.Signal(int)

    def __init__(self, *args, **kwargs):
        super(InstanceTreeView, self).__init__(*args, **kwargs)

        self.setObjectName("InstanceListView")
        self.setHeaderHidden(True)
        self.setIndentation(0)
        self.setExpandsOnDoubleClick(False)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.viewport().setMouseTracking(True)
        self._pressed_group_index = None

    def _expand_item(self, index, expand=None):
        is_expanded = self.isExpanded(index)
        if expand is None:
            expand = not is_expanded

        if expand != is_expanded:
            if expand:
                self.expand(index)
            else:
                self.collapse(index)

    def get_selected_instance_ids(self):
        """Ids of selected instances."""
        instance_ids = set()
        for index in self.selectionModel().selectedIndexes():
            instance_id = index.data(INSTANCE_ID_ROLE)
            if instance_id is not None:
                instance_ids.add(instance_id)
        return instance_ids

    def event(self, event):
        if not event.type() == QtCore.QEvent.KeyPress:
            pass

        elif event.key() == QtCore.Qt.Key_Space:
            self.toggle_requested.emit(-1)
            return True

        elif event.key() == QtCore.Qt.Key_Backspace:
            self.toggle_requested.emit(0)
            return True

        elif event.key() == QtCore.Qt.Key_Return:
            self.toggle_requested.emit(1)
            return True

        return super(InstanceTreeView, self).event(event)

    def _mouse_press(self, event):
        """Store index of pressed group.

        This is to be able change state of group and process mouse
        "double click" as 2x "single click".
        """
        if event.button() != QtCore.Qt.LeftButton:
            return

        pressed_group_index = None
        pos_index = self.indexAt(event.pos())
        if pos_index.data(IS_GROUP_ROLE):
            pressed_group_index = pos_index

        self._pressed_group_index = pressed_group_index

    def mousePressEvent(self, event):
        self._mouse_press(event)
        super(InstanceTreeView, self).mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self._mouse_press(event)
        super(InstanceTreeView, self).mouseDoubleClickEvent(event)

    def _mouse_release(self, event, pressed_index):
        if event.button() != QtCore.Qt.LeftButton:
            return False

        pos_index = self.indexAt(event.pos())
        if not pos_index.data(IS_GROUP_ROLE) or pressed_index != pos_index:
            return False

        if self.state() == QtWidgets.QTreeView.State.DragSelectingState:
            indexes = self.selectionModel().selectedIndexes()
            if len(indexes) != 1 or indexes[0] != pos_index:
                return False

        self._expand_item(pos_index)
        return True

    def mouseReleaseEvent(self, event):
        pressed_index = self._pressed_group_index
        self._pressed_group_index = None
        result = self._mouse_release(event, pressed_index)
        if not result:
            super(InstanceTreeView, self).mouseReleaseEvent(event)


class InstanceListView(AbstractInstanceView):
    """Widget providing abstract methods of AbstractInstanceView for list view.

    This is public access to and from list view.
    """
    def __init__(self, controller, parent):
        super(InstanceListView, self).__init__(parent)

        self.controller = controller

        instance_view = InstanceTreeView(self)
        instance_delegate = ListItemDelegate(instance_view)
        instance_view.setItemDelegate(instance_delegate)
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
        instance_view.toggle_requested.connect(self._on_toggle_request)

        self._group_items = {}
        self._group_widgets = {}
        self._widgets_by_id = {}
        self._group_by_instance_id = {}
        self._context_item = None
        self._context_widget = None

        self._instance_view = instance_view
        self._instance_delegate = instance_delegate
        self._instance_model = instance_model
        self._proxy_model = proxy_model

    def _on_expand(self, index):
        group_name = index.data(SORT_VALUE_ROLE)
        group_widget = self._group_widgets.get(group_name)
        if group_widget:
            group_widget.set_expanded(True)

    def _on_collapse(self, index):
        group_name = index.data(SORT_VALUE_ROLE)
        group_widget = self._group_widgets.get(group_name)
        if group_widget:
            group_widget.set_expanded(False)

    def _on_toggle_request(self, toggle):
        selected_instance_ids = self._instance_view.get_selected_instance_ids()
        if toggle == -1:
            active = None
        elif toggle == 1:
            active = True
        else:
            active = False

        group_names = set()
        for instance_id in selected_instance_ids:
            widget = self._widgets_by_id.get(instance_id)
            if widget is None:
                continue

            widget.set_active(active)
            group_name = self._group_by_instance_id.get(instance_id)
            if group_name is not None:
                group_names.add(group_name)

        for group_name in group_names:
            self._update_group_checkstate(group_name)

    def _update_group_checkstate(self, group_name):
        """Update checkstate of one group."""
        widget = self._group_widgets.get(group_name)
        if widget is None:
            return

        activity = None
        for instance_id, _group_name in self._group_by_instance_id.items():
            if _group_name != group_name:
                continue

            instance_widget = self._widgets_by_id.get(instance_id)
            if not instance_widget:
                continue

            if activity is None:
                activity = int(instance_widget.is_active())

            elif activity != instance_widget.is_active():
                activity = -1
                break

        if activity is None:
            return

        state = QtCore.Qt.PartiallyChecked
        if activity == 0:
            state = QtCore.Qt.Unchecked
        elif activity == 1:
            state = QtCore.Qt.Checked
        widget.set_checkstate(state)

    def refresh(self):
        """Refresh instances in the view."""
        # Prepare instances by their groups
        instances_by_group_name = collections.defaultdict(list)
        group_names = set()
        for instance in self.controller.instances:
            group_label = instance.creator_label
            group_names.add(group_label)
            instances_by_group_name[group_label].append(instance)

        # Sort view at the end of refresh
        # - is turned off until any change in view happens
        sort_at_the_end = False

        # Access to root item of main model
        root_item = self._instance_model.invisibleRootItem()

        # Create or use already existing context item
        # - context widget does not change so we don't have to update anything
        context_item = None
        if self._context_item is None:
            sort_at_the_end = True
            context_item = QtGui.QStandardItem()
            context_item.setData(0, SORT_VALUE_ROLE)
            context_item.setData(CONTEXT_ID, INSTANCE_ID_ROLE)

            root_item.appendRow(context_item)

            index = self._instance_model.index(
                context_item.row(), context_item.column()
            )
            proxy_index = self._proxy_model.mapFromSource(index)
            widget = ListContextWidget(self._instance_view)
            self._instance_view.setIndexWidget(proxy_index, widget)

            self._context_widget = widget
            self._context_item = context_item

        # Create new groups based on prepared `instances_by_group_name`
        new_group_items = []
        for group_name in group_names:
            if group_name in self._group_items:
                continue

            group_item = QtGui.QStandardItem()
            group_item.setData(group_name, SORT_VALUE_ROLE)
            group_item.setData(True, IS_GROUP_ROLE)
            group_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self._group_items[group_name] = group_item
            new_group_items.append(group_item)

        # Add new group items to root item if there are any
        if new_group_items:
            # Trigger sort at the end
            sort_at_the_end = True
            root_item.appendRows(new_group_items)

        # Create widget for each new group item and store it for future usage
        for group_item in new_group_items:
            index = self._instance_model.index(
                group_item.row(), group_item.column()
            )
            proxy_index = self._proxy_model.mapFromSource(index)
            group_name = group_item.data(SORT_VALUE_ROLE)
            widget = InstanceListGroupWidget(group_name, self._instance_view)
            widget.expand_changed.connect(self._on_group_expand_request)
            widget.toggle_requested.connect(self._on_group_toggle_request)
            self._group_widgets[group_name] = widget
            self._instance_view.setIndexWidget(proxy_index, widget)

        # Remove groups that are not available anymore
        for group_name in tuple(self._group_items.keys()):
            if group_name in group_names:
                continue

            group_item = self._group_items.pop(group_name)
            root_item.removeRow(group_item.row())
            widget = self._group_widgets.pop(group_name)
            widget.deleteLater()

        # Store which groups should be expanded at the end
        expand_groups = set()
        # Process changes in each group item
        # - create new instance, update existing and remove not existing
        for group_name, group_item in self._group_items.items():
            # Instance items to remove
            # - will contain all existing instance ids at the start
            # - instance ids may be removed when existing instances are checked
            to_remove = set()
            # Mapping of existing instances under group item
            existing_mapping = {}

            # Get group index to be able get children indexes
            group_index = self._instance_model.index(
                group_item.row(), group_item.column()
            )

            # Iterate over children indexes of group item
            for idx in range(group_item.rowCount()):
                index = self._instance_model.index(idx, 0, group_index)
                instance_id = index.data(INSTANCE_ID_ROLE)
                # Add all instance into `to_remove` set
                to_remove.add(instance_id)
                existing_mapping[instance_id] = idx

            # Collect all new instances that are not existing under group
            # New items
            new_items = []
            # Tuples of new instance and instance itself
            new_items_with_instance = []
            # Group activity (should be {-1;0;1} at the end)
            # - 0 when all instances are disabled
            # - 1 when all instances are enabled
            # - -1 when it's mixed
            activity = None
            for instance in instances_by_group_name[group_name]:
                instance_id = instance.id
                # Handle group activity
                if activity is None:
                    activity = int(instance["active"])
                elif activity == -1:
                    pass
                elif activity != instance["active"]:
                    activity = -1

                self._group_by_instance_id[instance_id] = group_name
                # Remove instance id from `to_remove` if already exists and
                #   trigger update of widget
                if instance_id in to_remove:
                    to_remove.remove(instance_id)
                    widget = self._widgets_by_id[instance_id]
                    widget.update_instance(instance)
                    continue

                # Create new item and store it as new
                item = QtGui.QStandardItem()
                item.setData(instance["subset"], SORT_VALUE_ROLE)
                item.setData(instance_id, INSTANCE_ID_ROLE)
                new_items.append(item)
                new_items_with_instance.append((item, instance))

            # Set checkstate of group checkbox
            state = QtCore.Qt.PartiallyChecked
            if activity == 0:
                state = QtCore.Qt.Unchecked
            elif activity == 1:
                state = QtCore.Qt.Checked

            widget = self._group_widgets[group_name]
            widget.set_checkstate(state)

            # Remove items that were not found
            idx_to_remove = []
            for instance_id in to_remove:
                idx_to_remove.append(existing_mapping[instance_id])

            # Remove them in reverse order to prevent row index changes
            for idx in reversed(sorted(idx_to_remove)):
                group_item.removeRows(idx, 1)

            # Cleanup instance related widgets
            for instance_id in to_remove:
                self._group_by_instance_id.pop(instance_id)
                widget = self._widgets_by_id.pop(instance_id)
                widget.deleteLater()

            # Process new instance items and add them to model and create
            #   their widgets
            if new_items:
                # Trigger sort at the end when new instances are available
                sort_at_the_end = True

                # Add items under group item
                group_item.appendRows(new_items)

                for item, instance in new_items_with_instance:
                    if not instance.has_valid_context:
                        expand_groups.add(group_name)
                    item_index = self._instance_model.index(
                        item.row(),
                        item.column(),
                        group_index
                    )
                    proxy_index = self._proxy_model.mapFromSource(item_index)
                    widget = InstanceListItemWidget(
                        instance, self._instance_view
                    )
                    widget.active_changed.connect(self._on_active_changed)
                    self._instance_view.setIndexWidget(proxy_index, widget)
                    self._widgets_by_id[instance.id] = widget

            # Trigger sort at the end of refresh
            if sort_at_the_end:
                self._proxy_model.sort(0)

        # Expand groups marked for expanding
        for group_name in expand_groups:
            group_item = self._group_items[group_name]
            proxy_index = self._proxy_model.mapFromSource(group_item.index())

            self._instance_view.expand(proxy_index)

    def refresh_instance_states(self):
        """Trigger update of all instances."""
        for widget in self._widgets_by_id.values():
            widget.update_instance_values()

    def _on_active_changed(self, changed_instance_id, new_value):
        selected_instances, _ = self.get_selected_items()

        selected_ids = set()
        found = False
        for instance in selected_instances:
            selected_ids.add(instance.id)
            if not found and instance.id == changed_instance_id:
                found = True

        if not found:
            selected_ids = set()
            selected_ids.add(changed_instance_id)

        self._change_active_instances(selected_ids, new_value)
        group_names = set()
        for instance_id in selected_ids:
            group_name = self._group_by_instance_id.get(instance_id)
            if group_name is not None:
                group_names.add(group_name)

        for group_name in group_names:
            self._update_group_checkstate(group_name)

    def _change_active_instances(self, instance_ids, new_value):
        if not instance_ids:
            return

        changed_ids = set()
        for instance_id in instance_ids:
            widget = self._widgets_by_id.get(instance_id)
            if widget:
                changed_ids.add(instance_id)
                widget.set_active(new_value)

        if changed_ids:
            self.active_changed.emit()

    def get_selected_items(self):
        """Get selected instance ids and context selection.

        Returns:
            tuple<list, bool>: Selected instance ids and boolean if context
                is selected.
        """
        instances = []
        context_selected = False
        instances_by_id = {
            instance.id: instance
            for instance in self.controller.instances
        }

        for index in self._instance_view.selectionModel().selectedIndexes():
            instance_id = index.data(INSTANCE_ID_ROLE)
            if not context_selected and instance_id == CONTEXT_ID:
                context_selected = True

            elif instance_id is not None:
                instance = instances_by_id.get(instance_id)
                if instance:
                    instances.append(instance)

        return instances, context_selected

    def _on_selection_change(self, *_args):
        self.selection_changed.emit()

    def _on_group_expand_request(self, group_name, expanded):
        group_item = self._group_items.get(group_name)
        if not group_item:
            return

        group_index = self._instance_model.index(
            group_item.row(), group_item.column()
        )
        proxy_index = self._proxy_model.mapFromSource(group_index)
        self._instance_view.setExpanded(proxy_index, expanded)

    def _on_group_toggle_request(self, group_name, state):
        if state == QtCore.Qt.PartiallyChecked:
            return

        if state == QtCore.Qt.Checked:
            active = True
        else:
            active = False

        group_item = self._group_items.get(group_name)
        if not group_item:
            return

        instance_ids = set()
        for row in range(group_item.rowCount()):
            item = group_item.child(row)
            instance_id = item.data(INSTANCE_ID_ROLE)
            if instance_id is not None:
                instance_ids.add(instance_id)

        self._change_active_instances(instance_ids, active)

        proxy_index = self._proxy_model.mapFromSource(group_item.index())
        if not self._instance_view.isExpanded(proxy_index):
            self._instance_view.expand(proxy_index)
