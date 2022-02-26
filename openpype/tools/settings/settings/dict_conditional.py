from Qt import QtWidgets

from .widgets import (
    ExpandingWidget,
    GridLabelWidget
)
from .wrapper_widgets import (
    WrapperWidget,
    CollapsibleWrapper,
    FormWrapper
)
from .base import BaseWidget
from openpype.tools.settings import CHILD_OFFSET


class DictConditionalWidget(BaseWidget):
    def create_ui(self):
        self.input_fields = []

        self._content_by_enum_value = {}
        self._last_enum_value = None

        self.label_widget = None
        self.body_widget = None
        self.content_widget = None
        self.content_layout = None
        self.enum_layout = None

        label = None
        if self.entity.is_dynamic_item:
            self._ui_as_dynamic_item()

        elif self.entity.use_label_wrap:
            self._ui_label_wrap()

        else:
            self._ui_item_base()
            label = self.entity.label

        self._parent_widget_by_entity_id = {}
        self._enum_key_by_wrapper_id = {}
        self._added_wrapper_ids = set()

        enum_layout = QtWidgets.QGridLayout()
        enum_layout.setContentsMargins(0, 0, 0, 0)
        enum_layout.setColumnStretch(0, 0)
        enum_layout.setColumnStretch(1, 1)

        all_children_layout = QtWidgets.QVBoxLayout()
        all_children_layout.setContentsMargins(0, 0, 0, 0)

        if self.entity.enum_is_horizontal:
            if self.entity.enum_on_right:
                self.content_layout.addLayout(all_children_layout, 0, 0)
                self.content_layout.addLayout(enum_layout, 0, 1)
                # Stretch combobox to minimum and expand value
                self.content_layout.setColumnStretch(0, 1)
                self.content_layout.setColumnStretch(1, 0)
            else:
                self.content_layout.addLayout(enum_layout, 0, 0)
                self.content_layout.addLayout(all_children_layout, 0, 1)
                # Stretch combobox to minimum and expand value
                self.content_layout.setColumnStretch(0, 0)
                self.content_layout.setColumnStretch(1, 1)

        else:
            # Expand content
            self.content_layout.setColumnStretch(0, 1)
            self.content_layout.addLayout(enum_layout, 0, 0)
            self.content_layout.addLayout(all_children_layout, 1, 0)

        self.enum_layout = enum_layout
        self.all_children_layout = all_children_layout

        # Add enum entity to layout mapping
        enum_entity = self.entity.enum_entity
        self._parent_widget_by_entity_id[enum_entity.id] = self.content_widget

        # Add rest of entities to wrapper mappings
        for enum_key, children in self.entity.gui_layout.items():
            parent_widget_by_entity_id = {}

            content_widget = QtWidgets.QWidget(self.content_widget)
            content_layout = QtWidgets.QGridLayout(content_widget)
            content_layout.setColumnStretch(0, 0)
            content_layout.setColumnStretch(1, 1)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(5)

            all_children_layout.addWidget(content_widget)

            self._content_by_enum_value[enum_key] = {
                "widget": content_widget,
                "layout": content_layout
            }

            self._prepare_entity_layouts(
                children,
                content_widget,
                parent_widget_by_entity_id
            )
            for item_id in parent_widget_by_entity_id.keys():
                self._enum_key_by_wrapper_id[item_id] = enum_key
            self._parent_widget_by_entity_id.update(parent_widget_by_entity_id)

        enum_input_field = self.create_ui_for_entity(
            self.category_widget, self.entity.enum_entity, self
        )
        self.enum_input_field = enum_input_field
        self.input_fields.append(enum_input_field)

        for item_key, children in self.entity.children.items():
            content_widget = self._content_by_enum_value[item_key]["widget"]
            for child_obj in children:
                self.input_fields.append(
                    self.create_ui_for_entity(
                        self.category_widget, child_obj, self
                    )
                )

        if self.entity.use_label_wrap and self.content_layout.count() == 0:
            self.body_widget.hide_toolbox(True)

        self.entity_widget.add_widget_to_layout(self, label)

    def _prepare_entity_layouts(
        self, gui_layout, widget, parent_widget_by_entity_id
    ):
        for child in gui_layout:
            if not isinstance(child, dict):
                parent_widget_by_entity_id[child.id] = widget
                continue

            if child["type"] == "collapsible-wrap":
                wrapper = CollapsibleWrapper(child, widget)

            elif child["type"] == "form":
                wrapper = FormWrapper(child, widget)

            else:
                raise KeyError(
                    "Unknown Wrapper type \"{}\"".format(child["type"])
                )

            parent_widget_by_entity_id[wrapper.id] = widget

            self._prepare_entity_layouts(
                child["children"], wrapper, parent_widget_by_entity_id
            )

    def _ui_item_base(self):
        self.setObjectName("DictInvisible")

        self.content_widget = self
        self.content_layout = QtWidgets.QGridLayout(self)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)

    def _ui_as_dynamic_item(self):
        content_widget = QtWidgets.QWidget(self)
        content_widget.setObjectName("DictAsWidgetBody")

        show_borders = str(int(self.entity.show_borders))
        content_widget.setProperty("show_borders", show_borders)

        label_widget = QtWidgets.QLabel(self.entity.label)
        label_widget.setObjectName("SettingsLabel")

        content_layout = QtWidgets.QGridLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        main_layout.addWidget(content_widget)

        self.label_widget = label_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

    def _ui_label_wrap(self):
        content_widget = QtWidgets.QWidget(self)
        content_widget.setObjectName("ContentWidget")

        if self.entity.highlight_content:
            content_state = "highlighted"
            bottom_margin = 5
        else:
            content_state = ""
            bottom_margin = 0
        content_widget.setProperty("content_state", content_state)
        content_layout_margins = (CHILD_OFFSET, 5, 0, bottom_margin)

        body_widget = ExpandingWidget(self.entity.label, self)
        label_widget = body_widget.label_widget
        body_widget.set_content_widget(content_widget)

        content_layout = QtWidgets.QGridLayout(content_widget)
        content_layout.setContentsMargins(*content_layout_margins)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(body_widget)

        self.label_widget = label_widget
        self.body_widget = body_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

        if self.entity.collapsible:
            if not self.entity.collapsed:
                body_widget.toggle_content()
        else:
            body_widget.hide_toolbox(hide_content=False)

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

    def add_widget_to_layout(self, widget, label=None):
        if not widget.entity:
            map_id = widget.id
        else:
            map_id = widget.entity.id

        is_enum_item = map_id == self.entity.enum_entity.id
        if is_enum_item:
            content_widget = self.content_widget
            content_layout = self.enum_layout

            if not label:
                content_layout.addWidget(widget, 0, 0, 1, 2)
                return

            label_widget = GridLabelWidget(label, widget)
            label_widget.input_field = widget
            widget.label_widget = label_widget
            content_layout.addWidget(label_widget, 0, 0, 1, 1)
            content_layout.addWidget(widget, 0, 1, 1, 1)
            return

        enum_value = self._enum_key_by_wrapper_id[map_id]
        content_widget = self._content_by_enum_value[enum_value]["widget"]
        content_layout = self._content_by_enum_value[enum_value]["layout"]

        wrapper = self._parent_widget_by_entity_id[map_id]
        if wrapper is not content_widget:
            wrapper.add_widget_to_layout(widget, label)
            if wrapper.id not in self._added_wrapper_ids:
                self.add_widget_to_layout(wrapper)
                self._added_wrapper_ids.add(wrapper.id)
            return

        row = content_layout.rowCount()
        if not label or isinstance(widget, WrapperWidget):
            content_layout.addWidget(widget, row, 0, 1, 2)
        else:
            label_widget = GridLabelWidget(label, widget)
            label_widget.input_field = widget
            widget.label_widget = label_widget
            content_layout.addWidget(label_widget, row, 0, 1, 1)
            content_layout.addWidget(widget, row, 1, 1, 1)

    def set_entity_value(self):
        for input_field in self.input_fields:
            input_field.set_entity_value()

        self._on_entity_change()

    def hierarchical_style_update(self):
        self.update_style()
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

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

        style_state = self.get_style_state(
            self.is_invalid,
            has_unsaved_changes,
            has_project_override,
            has_studio_override
        )
        if self._style_state == style_state:
            return

        self._style_state = style_state

        if self.body_widget:
            if style_state:
                child_style_state = "child-{}".format(style_state)
            else:
                child_style_state = ""

            self.body_widget.side_line_widget.setProperty(
                "state", child_style_state
            )
            self.body_widget.side_line_widget.style().polish(
                self.body_widget.side_line_widget
            )

        # There is nothing to care if there is no label
        if not self.label_widget:
            return

        # Don't change label if is not group or under group item
        if not self.entity.is_group and not self.entity.group_item:
            return

        self.label_widget.setProperty("state", style_state)
        self.label_widget.style().polish(self.label_widget)

    def _on_entity_change(self):
        enum_value = self.enum_input_field.entity.value
        if enum_value == self._last_enum_value:
            return

        self._last_enum_value = enum_value
        for item_key, content in self._content_by_enum_value.items():
            widget = content["widget"]
            widget.setVisible(item_key == enum_value)

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
