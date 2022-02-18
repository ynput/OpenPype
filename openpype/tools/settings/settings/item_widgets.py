import json

from Qt import QtWidgets, QtCore, QtGui

from openpype.widgets.sliders import NiceSlider
from openpype.tools.settings import CHILD_OFFSET
from openpype.settings.entities.exceptions import BaseInvalidValue

from .widgets import (
    ExpandingWidget,
    NumberSpinBox,
    GridLabelWidget,
    SettingsComboBox,
    SettingsPlainTextEdit,
    SettingsNiceCheckbox,
    SettingsLineEdit
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


class DictImmutableKeysWidget(BaseWidget):
    def create_ui(self):
        self.input_fields = []
        self.checkbox_child = None

        self.label_widget = None
        self.body_widget = None
        self.content_widget = None
        self.content_layout = None

        label = None
        if self.entity.is_dynamic_item:
            self._ui_as_dynamic_item()

        elif self.entity.use_label_wrap:
            self._ui_label_wrap()
            self.checkbox_child = self.entity.non_gui_children.get(
                self.entity.checkbox_key
            )

        else:
            self._ui_item_base()
            label = self.entity.label

        # Set stretch of second column to 1
        if isinstance(self.content_layout, QtWidgets.QGridLayout):
            self.content_layout.setColumnStretch(1, 1)

        self._direct_children_widgets = []
        self._parent_widget_by_entity_id = {}
        self._added_wrapper_ids = set()
        self._prepare_entity_layouts(
            self.entity.gui_layout, self.content_widget
        )

        for child_obj in self.entity.children:
            self.input_fields.append(
                self.create_ui_for_entity(
                    self.category_widget, child_obj, self
                )
            )

        if self.entity.use_label_wrap and self.content_layout.count() == 0:
            self.body_widget.hide_toolbox(True)

        self.entity_widget.add_widget_to_layout(self, label)

    def _prepare_entity_layouts(self, children, widget):
        for child in children:
            if not isinstance(child, dict):
                if child is not self.checkbox_child:
                    self._parent_widget_by_entity_id[child.id] = widget
                continue

            if child["type"] == "collapsible-wrap":
                wrapper = CollapsibleWrapper(child, widget)

            elif child["type"] == "form":
                wrapper = FormWrapper(child, widget)

            else:
                raise KeyError(
                    "Unknown Wrapper type \"{}\"".format(child["type"])
                )

            self._parent_widget_by_entity_id[wrapper.id] = widget

            self._prepare_entity_layouts(child["children"], wrapper)

    def set_focus(self, scroll_to=False):
        """Set focus of a widget.

        Args:
            scroll_to(bool): Also scroll to widget in category widget.
        """
        if self.body_widget:
            if scroll_to:
                self.scroll_to(self.body_widget.top_part)
            self.body_widget.top_part.setFocus()

        else:
            if scroll_to:
                if not self.input_fields:
                    self.scroll_to(self)
                else:
                    self.scroll_to(self.input_fields[0])
            self.setFocus()

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

        if len(self.input_fields) == 1 and self.checkbox_child:
            body_widget.hide_toolbox(hide_content=True)

        elif self.entity.collapsible:
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

        is_checkbox_child = False
        changed = False
        for direct_child in self._direct_children_widgets:
            if direct_child.make_sure_is_visible(path, scroll_to):
                changed = True
                if direct_child.entity is self.checkbox_child:
                    is_checkbox_child = True
                break

        # Change scroll to this widget
        if is_checkbox_child:
            self.scroll_to(self)

        elif self.body_widget and not self.body_widget.is_expanded():
            # Expand widget if is callapsible
            self.body_widget.toggle_content(True)

        return changed

    def add_widget_to_layout(self, widget, label=None):
        if self.checkbox_child and widget.entity is self.checkbox_child:
            self.body_widget.add_widget_before_label(widget)
            self._direct_children_widgets.append(widget)
            return

        if not widget.entity:
            map_id = widget.id
        else:
            map_id = widget.entity.id

        wrapper = self._parent_widget_by_entity_id[map_id]
        if wrapper is not self.content_widget:
            wrapper.add_widget_to_layout(widget, label)
            if wrapper.id not in self._added_wrapper_ids:
                self.add_widget_to_layout(wrapper)
                self._added_wrapper_ids.add(wrapper.id)
            return

        self._direct_children_widgets.append(widget)

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
    def _add_inputs_to_layout(self):
        self.input_field = SettingsNiceCheckbox(parent=self.content_widget)

        self.content_layout.addWidget(self.input_field, 0)
        self.content_layout.addStretch(1)

        self.setFocusProxy(self.input_field)

        self.input_field.focused_in.connect(self._on_input_focus)
        self.input_field.stateChanged.connect(self._on_value_change)

    def _on_input_focus(self):
        self.focused_in()

    def _on_entity_change(self):
        if self.entity.value != self.input_field.isChecked():
            self.set_entity_value()

    def set_entity_value(self):
        self.input_field.setChecked(self.entity.value)

    def _on_value_change(self):
        if self.ignore_input_changes:
            return
        self.start_value_timer()

    def _on_value_change_timer(self):
        self.entity.set(self.input_field.isChecked())


class TextWidget(InputWidget):
    def _add_inputs_to_layout(self):
        multiline = self.entity.multiline
        if multiline:
            self.input_field = SettingsPlainTextEdit(self.content_widget)
        else:
            self.input_field = SettingsLineEdit(self.content_widget)

        placeholder_text = self.entity.placeholder_text
        if placeholder_text:
            self.input_field.setPlaceholderText(placeholder_text)

        self.setFocusProxy(self.input_field)

        layout_kwargs = {}
        if multiline:
            layout_kwargs["alignment"] = QtCore.Qt.AlignTop

        self.content_layout.addWidget(self.input_field, 1, **layout_kwargs)

        self.input_field.focused_in.connect(self._on_input_focus)
        self.input_field.textChanged.connect(self._on_value_change)

        self._refresh_completer()

    def _refresh_completer(self):
        # Multiline entity can't have completer
        #   - there is not space for this UI component
        if self.entity.multiline:
            return

        self.input_field.update_completer_values(self.entity.value_hints)

    def _on_input_focus(self):
        self.focused_in()

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
        self.start_value_timer()

    def _on_value_change_timer(self):
        self.entity.set(self.input_value())


class OpenPypeVersionText(TextWidget):
    def __init__(self, *args, **kwargs):
        self._info_widget = None
        super(OpenPypeVersionText, self).__init__(*args, **kwargs)

    def create_ui(self):
        super(OpenPypeVersionText, self).create_ui()
        info_widget = QtWidgets.QLabel(self)
        info_widget.setObjectName("OpenPypeVersionLabel")
        self.content_layout.addWidget(info_widget, 1)

        self._info_widget = info_widget

    def _update_info_widget(self):
        value = self.input_value()

        message = ""
        tooltip = ""
        state = None
        if self._is_invalid:
            message = "Invalid OpenPype version format"

        elif value == "":
            message = "Use latest available version"
            tooltip = (
                "Latest version from OpenPype zip repository will be used"
            )

        elif value in self.entity.value_hints:
            state = "success"
            message = "Version {} will be used".format(value)

        else:
            state = "warning"
            message = (
                "Version {} not found in listed versions".format(value)
            )
            if self.entity.value_hints:
                tooltip = "Listed versions: {}".format(", ".join(
                    ['"{}"'.format(hint) for hint in self.entity.value_hints]
                ))
            else:
                tooltip = "No versions were listed"

        self._info_widget.setText(message)
        self._info_widget.setToolTip(tooltip)
        self.set_style_property(self._info_widget, "state", state)

    def set_entity_value(self):
        super(OpenPypeVersionText, self).set_entity_value()
        self._invalidate()
        self._update_info_widget()

    def _on_value_change_timer(self):
        value = self.input_value()
        self._invalidate()
        if not self.is_invalid:
            self.entity.set(value)
            self.update_style()
        else:
            # Manually trigger hierarchical style update
            self.ignore_input_changes.set_ignore(True)
            self.ignore_input_changes.set_ignore(False)

        self._update_info_widget()

    def _invalidate(self):
        value = self.input_value()
        try:
            self.entity.convert_to_valid_type(value)
            is_invalid = False
        except BaseInvalidValue:
            is_invalid = True
        self._is_invalid = is_invalid

    def _on_entity_change(self):
        super(OpenPypeVersionText, self)._on_entity_change()
        self._refresh_completer()


class NumberWidget(InputWidget):
    _slider_widget = None

    def _add_inputs_to_layout(self):
        kwargs = {
            "minimum": self.entity.minimum,
            "maximum": self.entity.maximum,
            "decimal": self.entity.decimal,
            "steps": self.entity.steps
        }
        self.input_field = NumberSpinBox(self.content_widget, **kwargs)
        input_field_stretch = 1

        slider_multiplier = 1
        if self.entity.show_slider:
            # Slider can't handle float numbers so all decimals are converted
            #   to integer range.
            slider_multiplier = 10 ** self.entity.decimal
            slider_widget = NiceSlider(QtCore.Qt.Horizontal, self)
            slider_widget.setRange(
                int(self.entity.minimum * slider_multiplier),
                int(self.entity.maximum * slider_multiplier)
            )
            if self.entity.steps is not None:
                slider_widget.setSingleStep(
                    self.entity.steps * slider_multiplier
                )

            self.content_layout.addWidget(slider_widget, 1)

            slider_widget.valueChanged.connect(self._on_slider_change)

            self._slider_widget = slider_widget

            input_field_stretch = 0

        self._slider_multiplier = slider_multiplier

        self.setFocusProxy(self.input_field)

        self.content_layout.addWidget(self.input_field, input_field_stretch)

        self.input_field.valueChanged.connect(self._on_value_change)
        self.input_field.focused_in.connect(self._on_input_focus)

        self._ignore_slider_change = False
        self._ignore_input_change = False

    def _on_input_focus(self):
        self.focused_in()

    def _on_entity_change(self):
        if self.entity.value != self.input_field.value():
            self.set_entity_value()

    def set_entity_value(self):
        self.input_field.setValue(self.entity.value)

    def _on_slider_change(self, new_value):
        if self._ignore_slider_change:
            return

        self._ignore_input_change = True
        self.input_field.setValue(new_value / self._slider_multiplier)
        self._ignore_input_change = False

    def _on_value_change(self):
        if self.ignore_input_changes:
            return

        self.start_value_timer()

    def _on_value_change_timer(self):
        value = self.input_field.value()
        if self._slider_widget is not None and not self._ignore_input_change:
            self._ignore_slider_change = True
            self._slider_widget.setValue(value * self._slider_multiplier)
            self._ignore_slider_change = False

        self.entity.set(value)


class RawJsonInput(SettingsPlainTextEdit):
    tab_length = 4

    def __init__(self, valid_type, *args, **kwargs):
        super(RawJsonInput, self).__init__(*args, **kwargs)
        self.setObjectName("RawJsonInput")
        self.setTabStopDistance(
            QtGui.QFontMetricsF(
                self.font()
            ).horizontalAdvance(" ") * self.tab_length
        )
        self.valid_type = valid_type

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
            value = self.json_value()
            return not isinstance(value, self.valid_type)
        except Exception:
            return True

    def resizeEvent(self, event):
        self.updateGeometry()
        super(RawJsonInput, self).resizeEvent(event)


class RawJsonWidget(InputWidget):
    def _add_inputs_to_layout(self):
        if self.entity.is_list:
            valid_type = list
        else:
            valid_type = dict
        self.input_field = RawJsonInput(valid_type, self.content_widget)
        self.input_field.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        self.setFocusProxy(self.input_field)

        self.content_layout.addWidget(
            self.input_field, 1, alignment=QtCore.Qt.AlignTop
        )

        self.input_field.focused_in.connect(self._on_input_focus)
        self.input_field.textChanged.connect(self._on_value_change)

    def _on_input_focus(self):
        self.focused_in()

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
        self.start_value_timer()

    def _on_value_change_timer(self):
        self._is_invalid = self.input_field.has_invalid_value()
        if not self.is_invalid:
            self.entity.set(self.input_field.json_value())
            self.update_style()
        else:
            # Manually trigger hierarchical style update
            self.ignore_input_changes.set_ignore(True)
            self.ignore_input_changes.set_ignore(False)


class EnumeratorWidget(InputWidget):
    def _add_inputs_to_layout(self):
        if self.entity.multiselection:
            self.input_field = MultiSelectionComboBox(
                placeholder=self.entity.placeholder, parent=self.content_widget
            )

        else:
            self.input_field = SettingsComboBox(self.content_widget)

        for enum_item in self.entity.enum_items:
            for value, label in enum_item.items():
                self.input_field.addItem(label, value)

        self.content_layout.addWidget(self.input_field, 0)

        self.setFocusProxy(self.input_field)

        self.input_field.focused_in.connect(self._on_input_focus)
        self.input_field.value_changed.connect(self._on_value_change)

    def _on_input_focus(self):
        self.focused_in()

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
        self._child_style_state = ""

        if self.entity.use_label_wrap:
            entity_label = None
            self._create_label_wrapper()
        else:
            entity_label = self.entity.label
            self.content_widget = self
            self.content_layout = QtWidgets.QGridLayout(self)
            self.content_layout.setContentsMargins(0, 0, 0, 0)
            self.content_layout.setSpacing(5)
            # Add stretch to second column
            self.content_layout.setColumnStretch(1, 1)
            self.body_widget = None

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.input_field = self.create_ui_for_entity(
            self.category_widget, self.entity.child_obj, self
        )
        self.entity_widget.add_widget_to_layout(self, entity_label)

    def _create_label_wrapper(self):
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        body_widget = ExpandingWidget(self.entity.label, self)
        main_layout.addWidget(body_widget)
        self.label_widget = body_widget.label_widget

        self.body_widget = body_widget

        content_widget = QtWidgets.QWidget(body_widget)
        content_widget.setObjectName("ContentWidget")
        content_widget.setProperty("content_state", "")
        content_layout = QtWidgets.QGridLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 5)

        body_widget.set_content_widget(content_widget)

        self.body_widget = body_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

        if not self.entity.collapsible:
            body_widget.hide_toolbox(hide_content=False)

        elif self.entity.collapsed:
            body_widget.toggle_content()

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

    def make_sure_is_visible(self, *args, **kwargs):
        return self.input_field.make_sure_is_visible(*args, **kwargs)

    def hierarchical_style_update(self):
        self.update_style()
        self.input_field.hierarchical_style_update()

    def _on_entity_change(self):
        # No need to do anything. Styles will be updated from top hierarchy.
        pass

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

    @property
    def is_invalid(self):
        return self._is_invalid or self.child_invalid

    @property
    def child_invalid(self):
        return self.input_field.is_invalid

    def get_invalid(self):
        return self.input_field.get_invalid()


class PathInputWidget(InputWidget):
    def _add_inputs_to_layout(self):
        self.input_field = SettingsLineEdit(self.content_widget)
        placeholder = self.entity.placeholder_text
        if placeholder:
            self.input_field.setPlaceholderText(placeholder)

        self.setFocusProxy(self.input_field)
        self.content_layout.addWidget(self.input_field)

        self.input_field.textChanged.connect(self._on_value_change)
        self.input_field.focused_in.connect(self._on_input_focus)

    def _on_input_focus(self):
        self.focused_in()

    def _on_entity_change(self):
        if self.entity.value != self.input_value():
            self.set_entity_value()

    def set_entity_value(self):
        self.input_field.setText(self.entity.value)

    def input_value(self):
        return self.input_field.text()

    def _on_value_change(self):
        if self.ignore_input_changes:
            return
        self.start_value_timer()

    def _on_value_change_timer(self):
        self.entity.set(self.input_value())
