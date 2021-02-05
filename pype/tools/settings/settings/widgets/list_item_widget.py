from Qt import QtWidgets, QtCore

from .base import InputWidget
from .widgets import ExpandingWidget
from .lib import (
    BTN_FIXED_SIZE,
    CHILD_OFFSET
)

from avalon.vendor import qtawesome


class EmptyListItem(QtWidgets.QWidget):
    def __init__(self, entity_widget, parent):
        super(EmptyListItem, self).__init__(parent)

        self.entity_widget = entity_widget

        add_btn = QtWidgets.QPushButton("+", self)
        remove_btn = QtWidgets.QPushButton("-", self)
        spacer_widget = QtWidgets.QWidget(self)
        spacer_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        add_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
        remove_btn.setEnabled(False)

        add_btn.setFixedSize(BTN_FIXED_SIZE, BTN_FIXED_SIZE)
        remove_btn.setFixedSize(BTN_FIXED_SIZE, BTN_FIXED_SIZE)

        add_btn.setProperty("btn-type", "tool-item")
        remove_btn.setProperty("btn-type", "tool-item")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(add_btn, 0)
        layout.addWidget(remove_btn, 0)
        layout.addWidget(spacer_widget, 1)

        add_btn.clicked.connect(self._on_add_clicked)

        self.add_btn = add_btn
        self.remove_btn = remove_btn
        self.spacer_widget = spacer_widget

    def _on_add_clicked(self):
        self.entity_widget.add_new_item()


class ListItem(QtWidgets.QWidget):
    def __init__(self, entity, entity_widget):
        super(ListItem, self).__init__(entity_widget.content_widget)
        self.entity_widget = entity_widget
        self.entity = entity

        self.ignore_input_changes = entity_widget.ignore_input_changes
        self.create_ui_for_entity = entity_widget.create_ui_for_entity

        char_up = qtawesome.charmap("fa.angle-up")
        char_down = qtawesome.charmap("fa.angle-down")

        add_btn = QtWidgets.QPushButton("+")
        remove_btn = QtWidgets.QPushButton("-")
        up_btn = QtWidgets.QPushButton(char_up)
        down_btn = QtWidgets.QPushButton(char_down)

        font_up_down = qtawesome.font("fa", 13)
        up_btn.setFont(font_up_down)
        down_btn.setFont(font_up_down)

        add_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
        remove_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
        up_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
        down_btn.setFocusPolicy(QtCore.Qt.ClickFocus)

        add_btn.setFixedSize(BTN_FIXED_SIZE, BTN_FIXED_SIZE)
        remove_btn.setFixedSize(BTN_FIXED_SIZE, BTN_FIXED_SIZE)
        up_btn.setFixedSize(BTN_FIXED_SIZE, BTN_FIXED_SIZE)
        down_btn.setFixedSize(BTN_FIXED_SIZE, BTN_FIXED_SIZE)

        add_btn.setProperty("btn-type", "tool-item")
        remove_btn.setProperty("btn-type", "tool-item")
        up_btn.setProperty("btn-type", "tool-item")
        down_btn.setProperty("btn-type", "tool-item")

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

        self.input_field = self.create_ui_for_entity(self.entity, self)
        self.input_field.set_entity_value()

        spacer_widget = QtWidgets.QWidget(self)
        spacer_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        spacer_widget.setVisible(False)

        layout.addWidget(spacer_widget, 1)

        layout.addWidget(up_btn, 0)
        layout.addWidget(down_btn, 0)

        self.add_btn = add_btn
        self.remove_btn = remove_btn
        self.up_btn = up_btn
        self.down_btn = down_btn

        self.spacer_widget = spacer_widget

    def get_invalid(self):
        return self.input_field.get_invalid()

    def add_widget_to_layout(self, widget, label=None):
        self.content_layout.addWidget(widget, 1)

    def row(self):
        return self.entity_widget.input_fields.index(self)

    def parent_rows_count(self):
        return len(self.entity_widget.input_fields)

    def _on_add_clicked(self):
        self.entity_widget.add_new_item(row=self.row() + 1)

    def _on_remove_clicked(self):
        self.entity_widget.remove_row(self)

    def _on_up_clicked(self):
        row = self.row()
        self.entity_widget.swap_rows(row - 1, row)

    def _on_down_clicked(self):
        row = self.row()
        self.entity_widget.swap_rows(row, row + 1)

    def order_changed(self):
        row = self.row()
        parent_row_count = self.parent_rows_count()
        if parent_row_count == 1:
            self.up_btn.setVisible(False)
            self.down_btn.setVisible(False)
            return

        if not self.up_btn.isVisible():
            self.up_btn.setVisible(True)
            self.down_btn.setVisible(True)

        if row == 0:
            self.up_btn.setEnabled(False)
            self.down_btn.setEnabled(True)

        elif row == parent_row_count - 1:
            self.up_btn.setEnabled(True)
            self.down_btn.setEnabled(False)

        else:
            self.up_btn.setEnabled(True)
            self.down_btn.setEnabled(True)

    def hierarchical_style_update(self):
        self.input_field.hierarchical_style_update()


class ListWidget(InputWidget):
    def create_ui(self):
        self._child_style_state = ""
        self.input_fields = []

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
        for input_field in tuple(self.input_fields):
            self.remove_row(input_field)

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

    def _on_entity_change(self):
        in_input_fields = list()
        for input_field in self.input_fields:
            in_input_fields.append(input_field.entity)

        for child_entity in self.entity:
            if child_entity not in in_input_fields:
                self.add_row(child_entity)
            else:
                in_input_fields.remove(child_entity)

        if in_input_fields:
            for input_field in tuple(self.input_fields):
                if input_field.entity in in_input_fields:
                    self.remove_row(input_field)

    def count(self):
        return len(self.input_fields)

    def swap_rows(self, row_1, row_2):
        if row_1 == row_2:
            return

        if row_1 > row_2:
            row_1, row_2 = row_2, row_1

        field_1 = self.input_fields[row_1]
        field_2 = self.input_fields[row_2]

        self.input_fields[row_1] = field_2
        self.input_fields[row_2] = field_1

        layout_index = self.content_layout.indexOf(field_1)
        self.content_layout.insertWidget(layout_index + 1, field_1)

        field_1.order_changed()
        field_2.order_changed()

    def add_new_item(self, row=None):
        child_entity = self.entity.add_new_item()
        child_entity.set_override_state(self.entity.override_state)

        self.add_row(child_entity)
        self.empty_row.setVisible(self.count() == 0)

    def add_row(self, child_entity, row=None):
        # Create new item
        item_widget = ListItem(child_entity, self)

        previous_field = None
        next_field = None

        if row is None:
            if self.input_fields:
                previous_field = self.input_fields[-1]
            self.content_layout.addWidget(item_widget)
            self.input_fields.append(item_widget)
        else:
            if row > 0:
                previous_field = self.input_fields[row - 1]

            max_index = self.count()
            if row < max_index:
                next_field = self.input_fields[row]

            self.content_layout.insertWidget(row, item_widget)
            self.input_fields.insert(row, item_widget)

        if previous_field:
            previous_field.order_changed()

        if next_field:
            next_field.order_changed()

        item_widget.order_changed()

        previous_input = None
        for input_field in self.input_fields:
            if previous_input is not None:
                self.setTabOrder(
                    previous_input, input_field.input_field.focusProxy()
                )
            previous_input = input_field.input_field.focusProxy()

        self.updateGeometry()

    def remove_row(self, item_widget):
        row = self.input_fields.index(item_widget)
        previous_field = None
        next_field = None
        if row > 0:
            previous_field = self.input_fields[row - 1]

        if row != len(self.input_fields) - 1:
            next_field = self.input_fields[row + 1]

        self.content_layout.removeWidget(item_widget)
        self.input_fields.pop(row)
        item_widget.setParent(None)
        item_widget.deleteLater()

        if previous_field:
            previous_field.order_changed()

        if next_field:
            next_field.order_changed()

        self.empty_row.setVisible(self.count() == 0)

        self.updateGeometry()

    def update_style(self):
        if not self.body_widget and not self.label_widget:
            return

        has_unsaved_changes = self.entity.has_unsaved_changes
        child_invalid = self.child_invalid
        has_project_override = self.entity.has_project_override
        has_studio_override = self.entity.has_studio_override

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
