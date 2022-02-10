from Qt import QtWidgets, QtCore

from .widgets import (
    GridLabelWidget,
    SpacerWidget
)
from .base import BaseWidget


class ListStrictWidget(BaseWidget):
    def create_ui(self):
        self.setObjectName("ListStrictWidget")

        self._child_style_state = ""
        self.input_fields = []

        content_layout = QtWidgets.QGridLayout(self)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(3)

        self.content_layout = content_layout
        self.content_widget = self

        any_children_has_label = False
        for child_obj in self.entity.children:
            if child_obj.label:
                any_children_has_label = True
                break

        self._any_children_has_label = any_children_has_label
        # Change column stretch factor for vertical alignment
        if not self.entity.is_horizontal:
            col_index = 2 if any_children_has_label else 1
            content_layout.setColumnStretch(col_index, 1)

        for child_obj in self.entity.children:
            self.input_fields.append(
                self.create_ui_for_entity(
                    self.category_widget, child_obj, self
                )
            )

        if self.entity.is_horizontal:
            col = self.content_layout.columnCount()
            spacer = SpacerWidget(self)
            self.content_layout.addWidget(spacer, 0, col, 2, 1)
            self.content_layout.setColumnStretch(col, 1)

        self.entity_widget.add_widget_to_layout(self, self.entity.label)

    @property
    def is_invalid(self):
        return self._is_invalid or self._child_invalid

    @property
    def _child_invalid(self):
        for input_field in self.input_fields:
            if input_field.is_invalid:
                return True
        return False

    def get_invalid(self):
        invalid = []
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

        if path.startswith(entity_path):
            for input_field in self.input_fields:
                if input_field.make_sure_is_visible(path, scroll_to):
                    return True
        return False

    def add_widget_to_layout(self, widget, label=None):
        # Horizontally added children
        if self.entity.is_horizontal:
            self._add_child_horizontally(widget, label)
        else:
            self._add_child_vertically(widget, label)

        self.updateGeometry()

    def _add_child_horizontally(self, widget, label):
        col = self.content_layout.columnCount()
        # Expand to whole grid if all children are without label
        if not self._any_children_has_label:
            self.content_layout.addWidget(widget, 0, col, 1, 2)
        else:
            if label:
                label_widget = GridLabelWidget(label, widget)
                label_widget.input_field = widget
                widget.label_widget = label_widget
                self.content_layout.addWidget(label_widget, 0, col, 1, 1)
                col += 1
            self.content_layout.addWidget(widget, 0, col, 1, 1)

    def _add_child_vertically(self, widget, label):
        row = self.content_layout.rowCount()
        if not self._any_children_has_label:
            self.content_layout.addWidget(widget, row, 0, 1, 1)

            spacer_widget = SpacerWidget(self)
            self.content_layout.addWidget(spacer_widget, row, 1, 1, 1)

        else:
            if label:
                label_widget = GridLabelWidget(label, widget)
                label_widget.input_field = widget
                widget.label_widget = label_widget
                self.content_layout.addWidget(
                    label_widget, row, 0, 1, 1,
                    alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignTop
                )
            self.content_layout.addWidget(widget, row, 1, 1, 1)

            spacer_widget = SpacerWidget(self)
            self.content_layout.addWidget(spacer_widget, row, 2, 1, 1)

    def hierarchical_style_update(self):
        self.update_style()
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

    def set_entity_value(self):
        for input_field in self.input_fields:
            input_field.set_entity_value()

    def _on_entity_change(self):
        pass

    def update_style(self):
        if not self.label_widget:
            return

        style_state = self.get_style_state(
            self.is_invalid,
            self.entity.has_unsaved_changes,
            self.entity.has_project_override,
            self.entity.has_studio_override
        )

        if self._style_state == style_state:
            return

        self.label_widget.setProperty("state", style_state)
        self.label_widget.style().polish(self.label_widget)

        self._style_state = style_state
