import json

from Qt import QtWidgets, QtCore, QtGui

from .widgets import (
    ExpandingWidget,
    NumberSpinBox,
    GridLabelWidget,
    ComboBox,
    NiceCheckbox
)
from .multiselection_combobox import MultiSelectionComboBox
from .wrapper_widgets import (
    WrapperWidget,
    CollapsibleWrapper,
    FormWrapper
)
from .base import (
    BaseWidget,
    InputWidget
)
from .lib import CHILD_OFFSET


class DictImmutableKeysWidget(BaseWidget):
    def create_ui(self):
        self._child_style_state = ""
        self.input_fields = []
        self.checkbox_child = None
        label = None
        if self.entity.is_dynamic_item:
            self._ui_item_or_as_widget()

        elif not self.entity.use_label_wrap:
            self._ui_item_without_label()
            label = self.entity.label

        else:
            self._ui_item_or_as_widget()
            self.checkbox_child = self.entity.non_gui_children.get(
                self.entity.checkbox_key
            )

        self.widget_mapping = {}
        self.wrapper_widgets_by_id = {}
        self._prepare_entity_layouts(
            self.entity.gui_layout, self.content_widget
        )

        for child_obj in self.entity.children:
            self.input_fields.append(
                self.create_ui_for_entity(
                    self.category_widget, child_obj, self
                )
            )

        self.entity_widget.add_widget_to_layout(self, label)

    def _prepare_entity_layouts(self, children, widget):
        for child in children:
            if not isinstance(child, dict):
                if child is not self.checkbox_child:
                    self.widget_mapping[child.id] = widget
                continue

            if child["type"] == "collapsible-wrap":
                wrapper = CollapsibleWrapper(child, widget)

            elif child["type"] == "form":
                wrapper = FormWrapper(child, widget)

            else:
                raise KeyError(
                    "Unknown Wrapper type \"{}\"".format(child["type"])
                )

            self.widget_mapping[wrapper.id] = widget
            self.wrapper_widgets_by_id[wrapper.id] = wrapper
            self.add_widget_to_layout(wrapper)
            self._prepare_entity_layouts(child["children"], wrapper)

    def _ui_item_without_label(self):
        self.setObjectName("DictInvisible")

        self.body_widget = None
        self.content_widget = self
        self.content_layout = QtWidgets.QGridLayout(self)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)

    def _ui_item_or_as_widget(self):
        content_widget = QtWidgets.QWidget(self)

        if self.entity.is_dynamic_item:
            content_widget.setObjectName("DictAsWidgetBody")
            show_borders = str(int(self.entity.show_borders))
            content_widget.setProperty("show_borders", show_borders)
            content_layout_margins = (5, 5, 5, 5)
            main_layout_spacing = 5
            body_widget = None
            label_widget = QtWidgets.QLabel(self.entity.label)

        else:
            content_widget.setObjectName("ContentWidget")
            if self.entity.highlight_content:
                content_state = "hightlighted"
                bottom_margin = 5
            else:
                content_state = ""
                bottom_margin = 0
            content_widget.setProperty("content_state", content_state)
            content_layout_margins = (CHILD_OFFSET, 5, 0, bottom_margin)
            main_layout_spacing = 0

            body_widget = ExpandingWidget(self.entity.label, self)
            label_widget = body_widget.label_widget
            body_widget.set_content_widget(content_widget)

        content_layout = QtWidgets.QGridLayout(content_widget)
        content_layout.setContentsMargins(*content_layout_margins)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(main_layout_spacing)
        if not body_widget:
            main_layout.addWidget(content_widget)
        else:
            main_layout.addWidget(body_widget)

        self.label_widget = label_widget
        self.body_widget = body_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

        if body_widget:
            if len(self.input_fields) == 1 and self.checkbox_widget:
                body_widget.hide_toolbox(hide_content=True)

            elif self.entity.collapsible:
                if not self.entity.collapsed:
                    body_widget.toggle_content()
            else:
                body_widget.hide_toolbox(hide_content=False)

    def add_widget_to_layout(self, widget, label=None):
        if self.checkbox_child and widget.entity is self.checkbox_child:
            self.body_widget.add_widget_before_label(widget)
            return

        if not widget.entity:
            map_id = widget.id
        else:
            map_id = widget.entity.id

        wrapper = self.widget_mapping[map_id]
        if wrapper is not self.content_widget:
            wrapper.add_widget_to_layout(widget, label)
            return

        row = self.content_layout.rowCount()
        if not label or isinstance(widget, WrapperWidget):
            self.content_layout.addWidget(widget, row, 0, 1, 2)
        else:
            label_widget = GridLabelWidget(label, widget)
            label_widget.input_field = widget
            widget.label_widget = label_widget
            self.content_layout.addWidget(label_widget, row, 0, 1, 1)
            self.content_layout.addWidget(widget, row, 1, 1, 1)

    def set_entity_value(self):
        for input_field in self.input_fields:
            input_field.set_entity_value()

    def hierarchical_style_update(self):
        self.update_style()
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

    def update_style(self, is_overriden=None):
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

        is_invalid = self.is_invalid
        if self.body_widget:
            child_style_state = self.get_style_state(
                is_invalid,
                has_unsaved_changes,
                has_project_override,
                has_studio_override
            )

            if child_style_state:
                child_style_state = "child-{}".format(child_style_state)

            if self._child_style_state != child_style_state:
                self.body_widget.side_line_widget.setProperty(
                    "state", child_style_state
                )
                self.body_widget.side_line_widget.style().polish(
                    self.body_widget.side_line_widget
                )
                self._child_style_state = child_style_state

        # There is nothing to care if there is no label
        if not self.label_widget:
            return
        # Don't change label if is not group or under group item
        if not self.entity.is_group and not self.entity.group_item:
            return

        style_state = self.get_style_state(
            is_invalid,
            has_unsaved_changes,
            has_project_override,
            has_studio_override
        )
        if self._style_state == style_state:
            return

        self.label_widget.setProperty("state", style_state)
        self.label_widget.style().polish(self.label_widget)

        self._style_state = style_state

    def _on_entity_change(self):
        pass

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


class BoolWidget(InputWidget):
    def create_ui(self):
        checkbox_height = self.style().pixelMetric(
            QtWidgets.QStyle.PM_IndicatorHeight
        )
        self.input_field = NiceCheckbox(height=checkbox_height, parent=self)

        spacer = QtWidgets.QWidget(self)
        spacer.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(self.input_field, 0)
        layout.addWidget(spacer, 1)

        self.setFocusProxy(self.input_field)

        self.input_field.stateChanged.connect(self._on_value_change)
        self.entity_widget.add_widget_to_layout(self, self.entity.label)

    def _on_entity_change(self):
        if self.entity.value != self.input_field.isChecked():
            self.set_entity_value()

    def set_entity_value(self):
        self.input_field.setChecked(self.entity.value)

    def _on_value_change(self):
        if self.ignore_input_changes:
            return
        self.entity.set(self.input_field.isChecked())


class TextWidget(InputWidget):
    def create_ui(self):
        multiline = self.entity.multiline
        if multiline:
            self.input_field = QtWidgets.QPlainTextEdit(self)
        else:
            self.input_field = QtWidgets.QLineEdit(self)

        placeholder_text = self.entity.placeholder_text
        if placeholder_text:
            self.input_field.setPlaceholderText(placeholder_text)

        self.setFocusProxy(self.input_field)

        layout_kwargs = {}
        if multiline:
            layout_kwargs["alignment"] = QtCore.Qt.AlignTop

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(self.input_field, 1, **layout_kwargs)

        self.input_field.textChanged.connect(self._on_value_change)

        self.entity_widget.add_widget_to_layout(self, self.entity.label)

    def _on_entity_change(self):
        if self.entity.value != self.input_value():
            self.set_entity_value()

    def set_entity_value(self):
        if self.entity.multiline:
            self.input_field.setPlainText(self.entity.value)
        else:
            self.input_field.setText(self.entity.value)

    def input_value(self):
        if self.entity.multiline:
            return self.input_field.toPlainText()
        else:
            return self.input_field.text()

    def _on_value_change(self):
        if self.ignore_input_changes:
            return

        self.entity.set(self.input_value())


class NumberWidget(InputWidget):
    def create_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        kwargs = {
            "minimum": self.entity.minimum,
            "maximum": self.entity.maximum,
            "decimal": self.entity.decimal
        }
        self.input_field = NumberSpinBox(self, **kwargs)

        self.setFocusProxy(self.input_field)

        layout.addWidget(self.input_field, 1)

        self.input_field.valueChanged.connect(self._on_value_change)

        self.entity_widget.add_widget_to_layout(self, self.entity.label)

    def _on_entity_change(self):
        if self.entity.value != self.input_field.value():
            self.set_entity_value()

    def set_entity_value(self):
        self.input_field.setValue(self.entity.value)

    def _on_value_change(self):
        if self.ignore_input_changes:
            return
        self.entity.set(self.input_field.value())


class RawJsonInput(QtWidgets.QPlainTextEdit):
    tab_length = 4

    def __init__(self, *args, **kwargs):
        super(RawJsonInput, self).__init__(*args, **kwargs)
        self.setObjectName("RawJsonInput")
        self.setTabStopDistance(
            QtGui.QFontMetricsF(
                self.font()
            ).horizontalAdvance(" ") * self.tab_length
        )

    def sizeHint(self):
        document = self.document()
        layout = document.documentLayout()

        height = document.documentMargin() + 2 * self.frameWidth() + 1
        block = document.begin()
        while block != document.end():
            height += layout.blockBoundingRect(block).height()
            block = block.next()

        hint = super(RawJsonInput, self).sizeHint()
        hint.setHeight(height)

        return hint

    def set_value(self, value):
        if not isinstance(value, str):
            try:
                value = json.dumps(value, indent=4)
            except Exception:
                value = ""
        self.setPlainText(value)

    def json_value(self):
        return json.loads(self.toPlainText())

    def has_invalid_value(self):
        try:
            self.json_value()
            return False
        except Exception:
            return True

    def resizeEvent(self, event):
        self.updateGeometry()
        super(RawJsonInput, self).resizeEvent(event)


class RawJsonWidget(InputWidget):
    def create_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.input_field = RawJsonInput(self)
        self.input_field.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        self.setFocusProxy(self.input_field)

        layout.addWidget(self.input_field, 1, alignment=QtCore.Qt.AlignTop)

        self.input_field.textChanged.connect(self._on_value_change)
        self.entity_widget.add_widget_to_layout(self, self.entity.label)

    def set_entity_value(self):
        self.input_field.set_value(self.entity.value)
        self._is_invalid = self.input_field.has_invalid_value()

    def _on_entity_change(self):
        if self.is_invalid:
            self.set_entity_value()
        else:
            if self.entity.value != self.input_field.json_value():
                self.set_entity_value()

    def _on_value_change(self):
        if self.ignore_input_changes:
            return

        self._is_invalid = self.input_field.has_invalid_value()
        if not self.is_invalid:
            self.entity.set(self.input_field.json_value())
            self.update_style()
        else:
            # Manually trigger hierachical style update
            self.ignore_input_changes.set_ignore(True)
            self.ignore_input_changes.set_ignore(False)


class EnumeratorWidget(InputWidget):
    def create_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if self.entity.multiselection:
            self.input_field = MultiSelectionComboBox(
                placeholder=self.entity.placeholder, parent=self
            )
            model = self.input_field.model()
            for idx in range(self.input_field.count()):
                model.item(idx).setCheckable(True)
        else:
            self.input_field = ComboBox(self)

        for enum_item in self.entity.enum_items:
            for value, label in enum_item.items():
                self.input_field.addItem(label, value)

        layout.addWidget(self.input_field, 0)

        self.setFocusProxy(self.input_field)

        self.input_field.value_changed.connect(self._on_value_change)
        self.entity_widget.add_widget_to_layout(self, self.entity.label)

    def _on_entity_change(self):
        if self.entity.value != self.input_field.value():
            self.set_entity_value()

    def set_entity_value(self):
        self.input_field.set_value(self.entity.value)

    def _on_value_change(self):
        if self.ignore_input_changes:
            return
        self.entity.set(self.input_field.value())


class PathWidget(BaseWidget):
    def create_ui(self):
        self.content_widget = self
        self.content_layout = QtWidgets.QGridLayout(self)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)

        self.input_field = self.create_ui_for_entity(
            self.category_widget, self.entity.child_obj, self
        )

        self.entity_widget.add_widget_to_layout(self, self.entity.label)

    def add_widget_to_layout(self, widget, label=None):
        row = self.content_layout.rowCount()
        if label:
            label_widget = GridLabelWidget(label, widget)
            label_widget.input_field = widget
            widget.label_widget = label_widget
            self.content_layout.addWidget(label_widget, row, 0, 1, 1)
            self.content_layout.addWidget(widget, row, 1, 1, 1)
        else:
            self.content_layout.addWidget(widget, row, 0, 1, 2)

    def set_entity_value(self):
        self.input_field.set_entity_value()

    def hierarchical_style_update(self):
        self.update_style()
        self.input_field.hierarchical_style_update()

    def _on_entity_change(self):
        # No need to do anything. Styles will be updated from top hierachy.
        pass

    def update_style(self):
        if not self.label_widget:
            return

        has_unsaved_changes = self.entity.has_unsaved_changes
        if not has_unsaved_changes and self.entity.group_item:
            has_unsaved_changes = self.entity.group_item.has_unsaved_changes

        state = self.get_style_state(
            self.is_invalid,
            has_unsaved_changes,
            self.entity.has_project_override,
            self.entity.has_studio_override
        )
        if self._style_state == state:
            return

        self._style_state = state

        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

    @property
    def is_invalid(self):
        return self._is_invalid or self.child_invalid

    @property
    def child_invalid(self):
        return self.input_field.is_invalid

    def get_invalid(self):
        return self.input_field.get_invalid()


class PathInputWidget(InputWidget):
    def create_ui(self, label_widget=None):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.input_field = QtWidgets.QLineEdit(self)
        self.args_input_field = None
        if self.entity.with_arguments:
            self.input_field.setPlaceholderText("Executable path")
            self.args_input_field = QtWidgets.QLineEdit(self)
            self.args_input_field.setPlaceholderText("Arguments")

        self.setFocusProxy(self.input_field)
        layout.addWidget(self.input_field, 8)
        self.input_field.textChanged.connect(self._on_value_change)

        if self.args_input_field:
            layout.addWidget(self.args_input_field, 2)
            self.args_input_field.textChanged.connect(self._on_value_change)

        self.entity_widget.add_widget_to_layout(self, self.entity.label)

    def _on_entity_change(self):
        if self.entity.value != self.input_value():
            self.set_entity_value()

    def set_entity_value(self):
        value = self.entity.value
        args = ""
        if isinstance(value, list):
            value, args = value
        self.input_field.setText(value)
        if self.args_input_field:
            self.args_input_field.setText(args)

    def input_value(self):
        path_value = self.input_field.text()
        if self.entity.with_arguments:
            value = [path_value, self.args_input_field.text()]
        else:
            value = path_value
        return value

    def _on_value_change(self):
        if self.ignore_input_changes:
            return
        self.entity.set(self.input_value())
