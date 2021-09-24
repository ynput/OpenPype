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
    """Generic delegate for instance header"""

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
        body_rect = QtCore.QRectF(option.rect)
        bg_rect = QtCore.QRectF(
            body_rect.left(), body_rect.top() + 1,
            body_rect.width() - 5, body_rect.height() - 2
        )

        expander_rect = QtCore.QRectF(bg_rect)
        expander_rect.setWidth(expander_rect.height())

        remainder_rect = QtCore.QRectF(
            expander_rect.x() + expander_rect.width(),
            expander_rect.y(),
            bg_rect.width() - expander_rect.width(),
            expander_rect.height()
        )

        ratio = bg_rect.height() * self.radius_ratio
        bg_path = QtGui.QPainterPath()
        bg_path.addRoundedRect(
            QtCore.QRectF(bg_rect), ratio, ratio
        )

        expander_colors = [self._group_colors["bg-expander"]]
        remainder_colors = [self._group_colors["bg"]]

        mouse_pos = option.widget.mapFromGlobal(QtGui.QCursor.pos())
        selected = option.state & QtWidgets.QStyle.State_Selected
        hovered = option.state & QtWidgets.QStyle.State_MouseOver

        if selected and hovered:
            if expander_rect.contains(mouse_pos):
                expander_colors.append(
                    self._group_colors["bg-expander-selected-hover"]
                )

            else:
                remainder_colors.append(
                    self._group_colors["bg-selected-hover"]
                )

        elif hovered:
            if expander_rect.contains(mouse_pos):
                expander_colors.append(
                    self._group_colors["bg-expander-hover"]
                )

            else:
                remainder_colors.append(
                    self._group_colors["bg-hover"]
                )

        # Draw backgrounds
        painter.save()
        painter.setClipRect(expander_rect)
        for color in expander_colors:
            painter.fillPath(bg_path, color)

        painter.setClipRect(remainder_rect)
        for color in remainder_colors:
            painter.fillPath(bg_path, color)
        painter.restore()

        # Draw text and icon
        widget = option.widget
        if widget:
            style = widget.style()
        else:
            style = QtWidgets.QApplication.style()
        font = index.data(QtCore.Qt.FontRole)
        if not font:
            font = option.font

        font_metrics = QtGui.QFontMetrics(font)

        text_height = expander_rect.height()
        adjust_value = (expander_rect.height() - text_height) / 2
        expander_rect.adjust(
            adjust_value + 1.5, adjust_value - 0.5,
            -adjust_value + 1.5, -adjust_value - 0.5
        )

        offset = (remainder_rect.height() - font_metrics.height()) / 2
        label_rect = QtCore.QRectF(remainder_rect.adjusted(
            5, offset - 1, 0, 0
        ))

        # if self.parent().isExpanded(index):
        #     expander_icon = icons["minus-sign"]
        # else:
        #     expander_icon = icons["plus-sign"]
        label = index.data(QtCore.Qt.DisplayRole)

        label = font_metrics.elidedText(
            label, QtCore.Qt.ElideRight, label_rect.width()
        )

        # Maintain reference to state, so we can restore it once we're done
        painter.save()

        # painter.setFont(fonts["awesome6"])
        # painter.setPen(QtGui.QPen(colors["idle"]))
        # painter.drawText(expander_rect, QtCore.Qt.AlignCenter, expander_icon)

        # Draw label
        painter.setFont(font)
        painter.drawText(label_rect, label)

        # Ok, we're done, tidy up.
        painter.restore()


class InstanceListItemWidget(QtWidgets.QWidget):
    active_changed = QtCore.Signal(str, bool)

    def __init__(self, instance, parent):
        super(InstanceListItemWidget, self).__init__(parent)

        self.instance = instance

        subset_name_label = QtWidgets.QLabel(instance.data["subset"], self)
        subset_name_label.setObjectName("ListViewSubsetName")

        active_checkbox = NiceCheckbox(parent=self)
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

        self._has_valid_context = None

        self._set_valid_property(instance.has_valid_context)

    def _set_valid_property(self, valid):
        if self._has_valid_context == valid:
            return
        self._has_valid_context = valid
        state = ""
        if not valid:
            state = "invalid"
        self.subset_name_label.setProperty("state", state)
        self.subset_name_label.style().polish(self.subset_name_label)

    def is_active(self):
        return self.instance.data["active"]

    def set_active(self, new_value):
        checkbox_value = self.active_checkbox.isChecked()
        instance_value = self.instance.data["active"]
        if new_value is None:
            new_value = not instance_value

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
        self._set_valid_property(self.instance.has_valid_context)

    def _on_active_change(self):
        new_value = self.active_checkbox.isChecked()
        old_value = self.instance.data["active"]
        if new_value == old_value:
            return

        self.instance.data["active"] = new_value
        self.active_changed.emit(self.instance.id, new_value)


class ListContextWidget(QtWidgets.QFrame):
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


class InstanceTreeView(QtWidgets.QTreeView):
    toggle_requested = QtCore.Signal(int)
    family_toggle_requested = QtCore.Signal(str)

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
        self._pressed_expander = None

    def _expand_item(self, index, expand=None):
        is_expanded = self.isExpanded(index)
        if expand is None:
            expand = not is_expanded

        if expand != is_expanded:
            if expand:
                self.expand(index)
            else:
                self.collapse(index)

    def _toggle_item(self, index):
        if index.data(IS_GROUP_ROLE):
            self.family_toggle_requested.emit(
                index.data(QtCore.Qt.DisplayRole)
            )

    def get_selected_instance_ids(self):
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

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        if index.data(IS_GROUP_ROLE):
            self.update(index)
        super(InstanceTreeView, self).mouseMoveEvent(event)

    def _mouse_press(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return

        pos_index = self.indexAt(event.pos())
        if not pos_index.data(IS_GROUP_ROLE):
            pressed_group_index = None
            pressed_expander = None
        else:
            height = self.indexRowSizeHint(pos_index)
            pressed_group_index = pos_index
            pressed_expander = event.pos().x() < height

        self._pressed_group_index = pressed_group_index
        self._pressed_expander = pressed_expander

    def mousePressEvent(self, event):
        if not self._mouse_press(event):
            super(InstanceTreeView, self).mousePressEvent(event)

    def _mouse_release(self, event, pressed_expander, pressed_index):
        if event.button() != QtCore.Qt.LeftButton:
            return False

        pos_index = self.indexAt(event.pos())
        if not pos_index.data(IS_GROUP_ROLE) or pressed_index != pos_index:
            return False

        if self.state() == QtWidgets.QTreeView.State.DragSelectingState:
            indexes = self.selectionModel().selectedIndexes()
            if len(indexes) != 1 or indexes[0] != pos_index:
                return False

        height = self.indexRowSizeHint(pos_index)
        if event.pos().x() < height:
            if pressed_expander:
                self._expand_item(pos_index)
                return True
        elif not pressed_expander:
            self._toggle_item(pos_index)
            self._expand_item(pos_index, True)
            return True

    def mouseReleaseEvent(self, event):
        pressed_index = self._pressed_group_index
        pressed_expander = self._pressed_expander is True
        self._pressed_group_index = None
        self._pressed_expander = None
        result = self._mouse_release(event, pressed_expander, pressed_index)
        if not result:
            super(InstanceTreeView, self).mouseReleaseEvent(event)


class InstanceListView(AbstractInstanceView):
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
        instance_view.family_toggle_requested.connect(
            self._on_family_toggle_request
        )

        self._group_items = {}
        self._group_widgets = {}
        self._widgets_by_id = {}
        self._context_item = None
        self._context_widget = None

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

    def _on_toggle_request(self, toggle):
        selected_instance_ids = self.instance_view.get_selected_instance_ids()
        if toggle == -1:
            active = None
        elif toggle == 1:
            active = True
        else:
            active = False

        for instance_id in selected_instance_ids:
            widget = self._widgets_by_id.get(instance_id)
            if widget is not None:
                widget.set_active(active)

    def _on_family_toggle_request(self, family):
        family_item = self._group_items.get(family)
        if not family_item:
            return

        instance_ids = []
        all_active = True
        for row in range(family_item.rowCount()):
            item = family_item.child(row, family_item.column())
            instance_id = item.data(INSTANCE_ID_ROLE)
            instance_ids.append(instance_id)
            if not all_active:
                continue

            widget = self._widgets_by_id.get(instance_id)
            if widget is not None and not widget.is_active():
                all_active = False

        active = not all_active
        for instance_id in instance_ids:
            widget = self._widgets_by_id.get(instance_id)
            if widget is not None:
                widget.set_active(active)

    def refresh(self):
        instances_by_family = collections.defaultdict(list)
        families = set()
        for instance in self.controller.instances:
            family = instance.data["family"]
            families.add(family)
            instances_by_family[family].append(instance)

        sort_at_the_end = False
        root_item = self.instance_model.invisibleRootItem()

        context_item = None
        if self._context_item is None:
            sort_at_the_end = True
            context_item = QtGui.QStandardItem()
            context_item.setData(0, SORT_VALUE_ROLE)
            context_item.setData(CONTEXT_ID, INSTANCE_ID_ROLE)

            root_item.appendRow(context_item)

            index = self.instance_model.index(
                context_item.row(), context_item.column()
            )
            proxy_index = self.proxy_model.mapFromSource(index)
            widget = ListContextWidget(self.instance_view)
            self.instance_view.setIndexWidget(proxy_index, widget)

            self._context_widget = widget
            self._context_item = context_item

        new_group_items = []
        for family in families:
            if family in self._group_items:
                continue

            group_item = QtGui.QStandardItem(family)
            group_item.setData(family, SORT_VALUE_ROLE)
            group_item.setData(True, IS_GROUP_ROLE)
            group_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self._group_items[family] = group_item
            new_group_items.append(group_item)

        if new_group_items:
            sort_at_the_end = True
            root_item.appendRows(new_group_items)

        for family in tuple(self._group_items.keys()):
            if family in families:
                continue

            group_item = self._group_items.pop(family)
            root_item.removeRow(group_item.row())

        expand_families = set()
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
                    if not instance.has_valid_context:
                        expand_families.add(family)
                    item_index = self.instance_model.index(
                        item.row(),
                        item.column(),
                        group_index
                    )
                    proxy_index = self.proxy_model.mapFromSource(item_index)
                    widget = InstanceListItemWidget(
                        instance, self.instance_view
                    )
                    widget.active_changed.connect(self._on_active_changed)
                    self.instance_view.setIndexWidget(proxy_index, widget)
                    self._widgets_by_id[instance.data["uuid"]] = widget

            # Trigger sort at the end of refresh
            if sort_at_the_end:
                self.proxy_model.sort(0)

        for family in expand_families:
            family_item = self._group_items[family]
            proxy_index = self.proxy_model.mapFromSource(family_item.index())

            self.instance_view.expand(proxy_index)

    def refresh_instance_states(self):
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

        changed_ids = set()
        for instance_id in selected_ids:
            widget = self._widgets_by_id.get(instance_id)
            if widget:
                changed_ids.add(instance_id)
                widget.set_active(new_value)

        if changed_ids:
            self.active_changed.emit()

    def get_selected_items(self):
        instances = []
        instances_by_id = {}
        context_selected = False
        for instance in self.controller.instances:
            instance_id = instance.data["uuid"]
            instances_by_id[instance_id] = instance

        for index in self.instance_view.selectionModel().selectedIndexes():
            instance_id = index.data(INSTANCE_ID_ROLE)
            if not context_selected and instance_id == CONTEXT_ID:
                context_selected = True

            elif instance_id is not None:
                instance = instances_by_id.get(instance_id)
                if instance:
                    instances.append(instance)

        return instances, context_selected

    def set_selected_items(self, instances, context_selected):
        instance_ids_by_family = collections.defaultdict(set)
        for instance in instances:
            family = instance.data["family"]
            instance_id = instance.data["uuid"]
            instance_ids_by_family[family].add(instance_id)

        indexes = []
        if context_selected and self._context_item is not None:
            index = self.instance_model.index(self._context_item.row(), 0)
            proxy_index = self.proxy_model.mapFromSource(index)
            indexes.append(proxy_index)

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
                index = self.proxy_model.index(row, 0, proxy_group_index)
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
