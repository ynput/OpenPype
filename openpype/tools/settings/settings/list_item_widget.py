from Qt import QtWidgets, QtCore

from openpype.tools.settings import (
    CHILD_OFFSET
)

from .base import InputWidget
from .widgets import ExpandingWidget
from .lib import (
    create_add_btn,
    create_remove_btn,
    create_up_btn,
    create_down_btn
)


class EmptyListItem(QtWidgets.QWidget):
    def __init__(self, entity_widget, parent):
        super(EmptyListItem, self).__init__(parent)

        self.entity_widget = entity_widget

        add_btn = create_add_btn(self)
        remove_btn = create_remove_btn(self)

        remove_btn.setEnabled(False)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(add_btn, 0)
        layout.addWidget(remove_btn, 0)
        layout.addStretch(1)

        add_btn.clicked.connect(self._on_add_clicked)

        self.add_btn = add_btn
        self.remove_btn = remove_btn

    def _on_add_clicked(self):
        self.entity_widget.add_new_item()


class ListItem(QtWidgets.QWidget):
    def __init__(self, entity, entity_widget):
        super(ListItem, self).__init__(entity_widget.content_widget)
        self.entity_widget = entity_widget
        self.entity = entity

        self.ignore_input_changes = entity_widget.ignore_input_changes

        add_btn = create_add_btn(self)
        remove_btn = create_remove_btn(self)
        up_btn = create_up_btn(self)
        down_btn = create_down_btn(self)

        add_btn.clicked.connect(self._on_add_clicked)
        remove_btn.clicked.connect(self._on_remove_clicked)
        up_btn.clicked.connect(self._on_up_clicked)
        down_btn.clicked.connect(self._on_down_clicked)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        layout.addWidget(add_btn, 0)
        layout.addWidget(remove_btn, 0)

        self.content_widget = self
        self.content_layout = layout

        self.input_field = self.create_ui_for_entity(
            self.category_widget, self.entity, self
        )

        layout.addWidget(up_btn, 0)
        layout.addWidget(down_btn, 0)

        self.add_btn = add_btn
        self.remove_btn = remove_btn
        self.up_btn = up_btn
        self.down_btn = down_btn

        self._row = -1
        self._is_last = False

    @property
    def category_widget(self):
        return self.entity_widget.category_widget

    def create_ui_for_entity(self, *args, **kwargs):
        return self.entity_widget.create_ui_for_entity(
            *args, **kwargs
        )

    def make_sure_is_visible(self, *args, **kwargs):
        return self.input_field.make_sure_is_visible(*args, **kwargs)

    @property
    def is_invalid(self):
        return self.input_field.is_invalid

    def get_invalid(self):
        return self.input_field.get_invalid()

    def add_widget_to_layout(self, widget, label=None):
        self.content_layout.addWidget(widget, 1)

    def set_row(self, row, is_last):
        if row == self._row and is_last == self._is_last:
            return

        trigger_order_changed = (
            row != self._row
            or is_last != self._is_last
        )
        self._row = row
        self._is_last = is_last

        if trigger_order_changed:
            self.order_changed()

    @property
    def row(self):
        return self._row

    def parent_rows_count(self):
        return len(self.entity_widget.input_fields)

    def _on_add_clicked(self):
        self.entity_widget.add_new_item(row=self.row + 1)

    def _on_remove_clicked(self):
        self.entity_widget.remove_row(self)

    def _on_up_clicked(self):
        self.entity_widget.swap_rows(self.row - 1, self.row)

    def _on_down_clicked(self):
        self.entity_widget.swap_rows(self.row, self.row + 1)

    def order_changed(self):
        parent_row_count = self.parent_rows_count()
        if parent_row_count == 1:
            self.up_btn.setVisible(False)
            self.down_btn.setVisible(False)
            return

        if not self.up_btn.isVisible():
            self.up_btn.setVisible(True)
            self.down_btn.setVisible(True)

        if self.row == 0:
            self.up_btn.setEnabled(False)
            self.down_btn.setEnabled(True)

        elif self.row == parent_row_count - 1:
            self.up_btn.setEnabled(True)
            self.down_btn.setEnabled(False)

        else:
            self.up_btn.setEnabled(True)
            self.down_btn.setEnabled(True)

    def hierarchical_style_update(self):
        self.input_field.hierarchical_style_update()

    def trigger_hierarchical_style_update(self):
        self.entity_widget.trigger_hierarchical_style_update()


class ListWidget(InputWidget):
    def create_ui(self):
        self._child_style_state = ""
        self.input_fields = []
        self._input_fields_by_entity_id = {}

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        body_widget = None
        entity_label = self.entity.label
        if self.entity.use_label_wrap:
            body_widget = ExpandingWidget(entity_label, self)
            entity_label = None
            main_layout.addWidget(body_widget)
            self.label_widget = body_widget.label_widget

        self.body_widget = body_widget

        if body_widget is None:
            content_parent_widget = self
        else:
            content_parent_widget = body_widget

        content_state = ""

        content_widget = QtWidgets.QWidget(content_parent_widget)
        content_widget.setObjectName("ContentWidget")
        content_widget.setProperty("content_state", content_state)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 5)

        if body_widget is None:
            main_layout.addWidget(content_widget)
        else:
            body_widget.set_content_widget(content_widget)

        self.body_widget = body_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

        if body_widget:
            if not self.entity.collapsible:
                body_widget.hide_toolbox(hide_content=False)

            elif self.entity.collapsed:
                body_widget.toggle_content()

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.empty_row = EmptyListItem(self, self.content_widget)
        self.content_layout.addWidget(self.empty_row)

        self.entity_widget.add_widget_to_layout(self, entity_label)

    def set_entity_value(self):
        self.remove_all_rows()

        for entity in self.entity.children:
            self.add_row(entity)

        self.empty_row.setVisible(self.count() == 0)

    def get_invalid(self):
        invalid = []
        if self.is_invalid:
            invalid.append(self)

        for input_field in self.input_fields:
            invalid.extend(input_field.get_invalid())
        return invalid

    def make_sure_is_visible(self, path, scroll_to):
        if not path:
            return False

        entity_path = self.entity.path
        if entity_path == path:
            self.set_focus(scroll_to)
            return True

        if not path.startswith(entity_path):
            return False

        if self.body_widget and not self.body_widget.is_expanded():
            self.body_widget.toggle_content(True)

        for input_field in self.input_fields:
            if input_field.make_sure_is_visible(path, scroll_to):
                return True
        return False

    def _on_entity_change(self):
        # TODO do less inefficient
        childen_order = []
        new_children = []
        for idx, child_entity in enumerate(self.entity):
            input_field = self._input_fields_by_entity_id.get(child_entity.id)
            if input_field is not None:
                childen_order.append(input_field)
            else:
                new_children.append((idx, child_entity))

        order_changed = False
        for idx, input_field in enumerate(childen_order):
            current_field = self.input_fields[idx]
            if current_field is input_field:
                continue
            order_changed = True
            old_idx = self.input_fields.index(input_field)
            self.input_fields[old_idx], self.input_fields[idx] = (
                current_field, input_field
            )
            self.content_layout.insertWidget(idx + 1, input_field)

        kept_len = len(childen_order)
        fields_len = len(self.input_fields)
        if fields_len > kept_len:
            order_changed = True
            for row in reversed(range(kept_len, fields_len)):
                self.remove_row(row=row)

        for idx, child_entity in new_children:
            order_changed = False
            self.add_row(child_entity, idx)

        if not order_changed:
            return

        self._on_order_change()

        input_field_len = self.count()
        self.empty_row.setVisible(input_field_len == 0)

    def _on_order_change(self):
        last_idx = self.count() - 1
        previous_input = None
        for idx, input_field in enumerate(self.input_fields):
            input_field.set_row(idx, idx == last_idx)
            next_input = input_field.input_field.focusProxy()
            if previous_input is not None:
                self.setTabOrder(previous_input, next_input)
            else:
                self.setTabOrder(self, next_input)
            previous_input = next_input

        if previous_input is not None:
            self.setTabOrder(previous_input, self)

    def count(self):
        return len(self.input_fields)

    def swap_rows(self, row_1, row_2):
        if row_1 == row_2:
            return

        self.entity.swap_indexes(row_1, row_2)

    def add_new_item(self, row=None):
        new_entity = self.entity.add_new_item(row)
        input_field = self._input_fields_by_entity_id.get(new_entity.id)
        if input_field is not None:
            input_field.input_field.setFocus()
        return new_entity

    def add_row(self, child_entity, row=None):
        # Create new item
        item_widget = ListItem(child_entity, self)
        self._input_fields_by_entity_id[child_entity.id] = item_widget

        if row is None:
            self.content_layout.addWidget(item_widget)
            self.input_fields.append(item_widget)
        else:
            self.content_layout.insertWidget(row + 1, item_widget)
            self.input_fields.insert(row, item_widget)

        # Change to entity value after item is added to `input_fields`
        # - may cause recursion error as setting a value may cause input field
        #   change which will trigger this validation if entity is already
        #   added as widget here which won't because is not in input_fields
        item_widget.input_field.set_entity_value()

        self._on_order_change()

        input_field_len = self.count()
        self.empty_row.setVisible(input_field_len == 0)

        self.updateGeometry()

    def remove_all_rows(self):
        self._input_fields_by_entity_id = {}
        while self.input_fields:
            item_widget = self.input_fields.pop(0)
            self.content_layout.removeWidget(item_widget)
            item_widget.setParent(None)
            item_widget.deleteLater()

        self.empty_row.setVisible(True)

        self.updateGeometry()

    def remove_row(self, item_widget=None, row=None):
        if item_widget is None:
            item_widget = self.input_fields[row]
        elif row is None:
            row = self.input_fields.index(item_widget)

        self.content_layout.removeWidget(item_widget)
        self.input_fields.pop(row)
        self._input_fields_by_entity_id.pop(item_widget.entity.id)
        item_widget.setParent(None)
        item_widget.deleteLater()

        if item_widget.entity in self.entity:
            self.entity.remove(item_widget.entity)

        rows = self.count()
        any_item = rows == 0
        if any_item:
            start_row = 0
            if row > 0:
                start_row = row - 1

            last_row = rows - 1
            _enum = enumerate(self.input_fields[start_row:rows])
            for idx, _item_widget in _enum:
                _item_widget.set_row(idx, idx == last_row)

        self.empty_row.setVisible(any_item)

        self.updateGeometry()

    @property
    def is_invalid(self):
        return self._is_invalid or self.child_invalid

    @property
    def child_invalid(self):
        for input_field in self.input_fields:
            if input_field.is_invalid:
                return True
        return False

    def update_style(self):
        if not self.body_widget and not self.label_widget:
            return

        if self.entity.group_item:
            group_item = self.entity.group_item
            has_unsaved_changes = group_item.has_unsaved_changes
            has_project_override = group_item.has_project_override
            has_studio_override = group_item.has_studio_override
        else:
            has_unsaved_changes = self.entity.has_unsaved_changes
            has_project_override = self.entity.has_project_override
            has_studio_override = self.entity.has_studio_override

        child_invalid = self.is_invalid

        if self.body_widget:
            child_style_state = self.get_style_state(
                child_invalid,
                has_unsaved_changes,
                has_project_override,
                has_studio_override
            )
            if child_style_state:
                child_style_state = "child-{}".format(child_style_state)

            if child_style_state != self._child_style_state:
                self.body_widget.side_line_widget.setProperty(
                    "state", child_style_state
                )
                self.body_widget.side_line_widget.style().polish(
                    self.body_widget.side_line_widget
                )
                self._child_style_state = child_style_state

        if self.label_widget:
            style_state = self.get_style_state(
                child_invalid,
                has_unsaved_changes,
                has_project_override,
                has_studio_override
            )
            if self._style_state != style_state:
                self.label_widget.setProperty("state", style_state)
                self.label_widget.style().polish(self.label_widget)

                self._style_state = style_state

    def hierarchical_style_update(self):
        self.update_style()
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
