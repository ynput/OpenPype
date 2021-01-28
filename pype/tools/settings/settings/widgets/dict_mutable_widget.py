from Qt import QtWidgets, QtCore

from .base import BaseWidget
from .widgets import (
    ExpandingWidget,
    IconButton,
    SpacerWidget
)
from .lib import (
    BTN_FIXED_SIZE,
    CHILD_OFFSET
)

from pype.settings.entities import NOT_SET


def create_add_btn(parent):
    add_btn = QtWidgets.QPushButton("+", parent)
    add_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
    add_btn.setProperty("btn-type", "tool-item")
    add_btn.setFixedSize(BTN_FIXED_SIZE, BTN_FIXED_SIZE)
    return add_btn


def create_remove_btn(parent):
    remove_btn = QtWidgets.QPushButton("-", parent)
    remove_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
    remove_btn.setProperty("btn-type", "tool-item")
    remove_btn.setFixedSize(BTN_FIXED_SIZE, BTN_FIXED_SIZE)
    return remove_btn


class ModifiableDictEmptyItem(QtWidgets.QWidget):
    def __init__(self, entity_widget, parent):
        super(ModifiableDictEmptyItem, self).__init__(parent)
        self.entity_widget = entity_widget
        self.collapsible_key = entity_widget.entity.collapsible
        if self.collapsible_key:
            self.create_collapsible_ui()
        else:
            self.create_addible_ui()

    def add_new_item(self, key=None, label=None):
        self.entity_widget.add_new_key(key, label)

    def _on_add_clicked(self):
        self.add_new_item()

    def create_addible_ui(self):
        add_btn = create_add_btn(self)
        remove_btn = create_remove_btn(self)
        spacer_widget = SpacerWidget(self)

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

    def _on_focus_lose(self):
        if self.key_input.hasFocus() or self.key_label_input.hasFocus():
            return
        self._on_enter_press()

    def _on_enter_press(self):
        if not self.collapsible_key:
            return

        key = self.key_input.text()
        if key:
            label = self.key_label_input.text()
            self.add_new_item(key, label)

    def _on_key_change(self):
        key = self.key_input.text()
        # TODO check if key is duplicated

    def create_collapsible_ui(self):
        key_input = QtWidgets.QLineEdit(self)
        key_input.setObjectName("DictKey")

        key_label_input = QtWidgets.QLineEdit(self)

        def key_input_focused_out(event):
            QtWidgets.QLineEdit.focusOutEvent(key_input, event)
            self._on_focus_lose()

        def key_label_input_focused_out(event):
            QtWidgets.QLineEdit.focusOutEvent(key_label_input, event)
            self._on_focus_lose()

        key_input.focusOutEvent = key_input_focused_out
        key_label_input.focusOutEvent = key_label_input_focused_out

        key_input_label_widget = QtWidgets.QLabel("Key:", self)
        key_label_input_label_widget = QtWidgets.QLabel("Label:", self)

        wrapper_widget = ExpandingWidget("", self)
        wrapper_widget.add_widget_after_label(key_input_label_widget)
        wrapper_widget.add_widget_after_label(key_input)
        wrapper_widget.add_widget_after_label(key_label_input_label_widget)
        wrapper_widget.add_widget_after_label(key_label_input)
        wrapper_widget.hide_toolbox()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(wrapper_widget)

        key_input.returnPressed.connect(self._on_enter_press)
        key_label_input.returnPressed.connect(self._on_enter_press)

        self.key_input = key_input
        self.key_label_input = key_label_input
        self.wrapper_widget = wrapper_widget


class ModifiableDictItem(QtWidgets.QWidget):
    def __init__(self, collapsible_key, entity, entity_widget):
        super(ModifiableDictItem, self).__init__(entity_widget.content_widget)

        self.collapsible_key = collapsible_key
        self.entity = entity
        self.entity_widget = entity_widget

        self.create_ui_for_entity = entity_widget.create_ui_for_entity
        self.ignore_input_changes = entity_widget.ignore_input_changes

        self.is_key_duplicated = False
        self.is_required = False

        self.origin_key = NOT_SET
        self.origin_key_label = NOT_SET

        self._style_state = ""

        if collapsible_key:
            self.create_collapsible_ui()
        else:
            self.create_addible_ui()

    def create_addible_ui(self):
        key_input = QtWidgets.QLineEdit(self)
        key_input.setObjectName("DictKey")

        spacer_widget = SpacerWidget(self)
        spacer_widget.setVisible(False)

        add_btn = create_add_btn(self)
        remove_btn = create_remove_btn(self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(add_btn, 0)
        layout.addWidget(remove_btn, 0)
        layout.addWidget(key_input, 0)
        layout.addWidget(spacer_widget, 1)

        key_input.textChanged.connect(self._on_key_change)
        key_input.returnPressed.connect(self._on_enter_press)

        add_btn.clicked.connect(self.on_add_clicked)
        remove_btn.clicked.connect(self.on_remove_clicked)

        self.key_input = key_input
        self.spacer_widget = spacer_widget
        self.add_btn = add_btn
        self.remove_btn = remove_btn

        self.content_widget = self
        self.content_layout = layout

        self.input_field = self.create_ui_for_entity(self.entity, self)

    def add_widget_to_layout(self, widget, label=None):
        self.content_layout.addWidget(widget)
        self.setFocusProxy(widget)

    def create_collapsible_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        key_input = QtWidgets.QLineEdit(self)
        key_input.setObjectName("DictKey")

        key_label_input = QtWidgets.QLineEdit(self)

        wrapper_widget = ExpandingWidget("", self)
        layout.addWidget(wrapper_widget)

        content_widget = QtWidgets.QWidget(wrapper_widget)
        content_widget.setObjectName("ContentWidget")
        content_layout = QtWidgets.QHBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)
        content_layout.setSpacing(5)

        wrapper_widget.set_content_widget(content_widget)

        def key_input_focused_out(event):
            QtWidgets.QLineEdit.focusOutEvent(key_input, event)
            self._on_focus_lose()

        def key_label_input_focused_out(event):
            QtWidgets.QLineEdit.focusOutEvent(key_label_input, event)
            self._on_focus_lose()

        key_input.focusOutEvent = key_input_focused_out
        key_label_input.focusOutEvent = key_label_input_focused_out

        edit_btn = IconButton(
            "fa.edit", QtCore.Qt.lightGray, QtCore.Qt.white
        )
        edit_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
        edit_btn.setProperty("btn-type", "tool-item-icon")
        edit_btn.setFixedHeight(BTN_FIXED_SIZE)

        remove_btn = create_remove_btn(self)

        key_input_label_widget = QtWidgets.QLabel("Key:")
        key_label_input_label_widget = QtWidgets.QLabel("Label:")
        wrapper_widget.add_widget_before_label(edit_btn)
        wrapper_widget.add_widget_after_label(key_input_label_widget)
        wrapper_widget.add_widget_after_label(key_input)
        wrapper_widget.add_widget_after_label(key_label_input_label_widget)
        wrapper_widget.add_widget_after_label(key_label_input)
        wrapper_widget.add_widget_after_label(remove_btn)

        key_input.textChanged.connect(self._on_key_change)
        key_input.returnPressed.connect(self._on_enter_press)

        key_label_input.textChanged.connect(self._on_key_change)
        key_label_input.returnPressed.connect(self._on_enter_press)

        edit_btn.clicked.connect(self.on_edit_pressed)
        remove_btn.clicked.connect(self.on_remove_clicked)

        self.key_input = key_input
        self.key_input_label_widget = key_input_label_widget
        self.key_label_input = key_label_input
        self.key_label_input_label_widget = key_label_input_label_widget
        self.wrapper_widget = wrapper_widget
        self.edit_btn = edit_btn
        self.remove_btn = remove_btn

        self.content_widget = content_widget
        self.content_layout = content_layout

        self.input_field = self.create_ui_for_entity(self.entity, self)

    def get_style_state(self):
        if self.is_invalid:
            return "invalid"
        if self.entity.has_unsaved_changes:
            return "modified"
        if self.entity.has_project_override:
            return "overriden"
        if self.entity.has_studio_override:
            return "studio"
        return ""

    def key_value(self):
        return self.key_input.text()

    def is_key_invalid(self):
        if self.is_key_duplicated or self.key_value() == "":
            return True
        return False

    def set_key_is_duplicated(self, duplicated):
        if duplicated == self.is_key_duplicated:
            return

        self.is_key_duplicated = duplicated
        if self.collapsible_key:
            if duplicated:
                self.set_edit_mode(True)
            else:
                self._on_focus_lose()
        self.update_style()

    def set_as_required(self, key):
        self.key_input.setText(key)
        self.key_input.setEnabled(False)
        self.is_required = True

        if self.collapsible_key:
            self.remove_btn.setVisible(False)
        else:
            self.remove_btn.setEnabled(False)
            self.add_btn.setEnabled(False)

    def set_as_last_required(self):
        self.add_btn.setEnabled(True)

    def _on_focus_lose(self):
        if (
            self.edit_btn.hasFocus()
            or self.key_input.hasFocus()
            or self.key_label_input.hasFocus()
            or self.remove_btn.hasFocus()
        ):
            return
        self._on_enter_press()

    def _on_enter_press(self):
        if not self.collapsible_key:
            return

        if self._is_empty:
            self.on_add_clicked()
        else:
            self.set_edit_mode(False)

    def _on_key_label_change(self):
        self.update_key_label()

    def _on_key_change(self):
        self.update_key_label()

        self._on_value_change()

    @property
    def value_is_env_group(self):
        return self._parent.value_is_env_group

    def update_key_label(self):
        if not self.wrapper_widget:
            return
        key_value = self.key_input.text()
        key_label_value = self.key_label_input.text()
        if key_label_value:
            label = "{} ({})".format(key_label_value, key_value)
        else:
            label = key_value
        self.wrapper_widget.label_widget.setText(label)

    def on_add_clicked(self):
        if not self.collapsible_key:
            self.entity_widget.add_new_key(row=self.row() + 1)
            return

        if not self.key_value():
            return

        self.entity_widget.add_row(row=self.row() + 1, is_empty=True)

    def on_edit_pressed(self):
        if not self.key_input.isVisible():
            self.set_edit_mode()
        else:
            self.key_input.setFocus()

    def set_edit_mode(self, enabled=True):
        if self.is_invalid and not enabled:
            return
        self.wrapper_widget.label_widget.setVisible(not enabled)
        self.key_label_input_label_widget.setVisible(enabled)
        self.key_input.setVisible(enabled)
        self.key_input_label_widget.setVisible(enabled)
        self.key_label_input.setVisible(enabled)
        if not self.is_required:
            self.remove_btn.setVisible(enabled)
        if enabled:
            if self.key_input.isEnabled():
                self.key_input.setFocus()
            else:
                self.key_label_input.setFocus()

    def on_remove_clicked(self):
        self._parent.remove_row(self)

    def is_key_modified(self):
        return self.key_value() != self.origin_key

    def is_key_label_modified(self):
        return self.key_label_value() != self.origin_key_label

    def is_value_modified(self):
        return self.input_field.is_modified

    @property
    def is_modified(self):
        return (
            self.is_key_modified()
            or self.is_key_label_modified()
            or self.is_value_modified()
        )

    def hierarchical_style_update(self):
        self.input_field.hierarchical_style_update()
        self.update_style()

    @property
    def is_invalid(self):
        return self.is_key_invalid() or self.input_field.is_invalid

    def update_style(self):
        key_input_state = ""
        if not self._is_empty:
            if self.is_key_invalid():
                key_input_state = "invalid"
            elif self.is_key_modified():
                key_input_state = "modified"

        self.key_input.setProperty("state", key_input_state)
        self.key_input.style().polish(self.key_input)

        if not self.wrapper_widget:
            return

        state = self.get_style_state()

        if self._style_state == state:
            return

        self._style_state = state

        if self.wrapper_widget.label_widget:
            self.wrapper_widget.label_widget.setProperty("state", state)
            self.wrapper_widget.label_widget.style().polish(
                self.wrapper_widget.label_widget
            )

        if state:
            child_state = "child-{}".format(state)
        else:
            child_state = ""

        self.wrapper_widget.side_line_widget.setProperty("state", child_state)
        self.wrapper_widget.side_line_widget.style().polish(
            self.wrapper_widget.side_line_widget
        )

    def row(self):
        return self._parent.input_fields.index(self)

    def key_label_value(self):
        if self.collapsible_key:
            return self.key_label_input.text()
        return NOT_SET

    def mouseReleaseEvent(self, event):
        return QtWidgets.QWidget.mouseReleaseEvent(self, event)


class DictMutableKeysWidget(BaseWidget):
    def create_ui(self):
        self.input_fields = []
        self.required_inputs_by_key = {}

        if self.entity.hightlight_content:
            content_state = "hightlighted"
            bottom_margin = 5
        else:
            content_state = ""
            bottom_margin = 0

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        label = self.entity.label
        body_widget = None
        if label:
            body_widget = ExpandingWidget(label, self)
            main_layout.addWidget(body_widget)
            label = None
            self.label_widget = body_widget.label_widget

        if body_widget is None:
            content_parent_widget = self
        else:
            content_parent_widget = body_widget

        content_widget = QtWidgets.QWidget(content_parent_widget)
        content_widget.setObjectName("ContentWidget")
        content_widget.setProperty("content_state", content_state)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, bottom_margin)

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
            elif not self.entity.collapsed:
                body_widget.toggle_content()

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.add_required_keys()

        self.empty_row = ModifiableDictEmptyItem(
            self, self.content_widget
        )
        self.content_layout.addWidget(self.empty_row)

        self.entity_widget.add_widget_to_layout(self, label)

    def add_required_keys(self):
        # TODO implement
        pass

    def add_new_key(self, key, label=None, after_widget=None):
        new_widget_index = 0
        if self.input_fields:
            if not after_widget:
                after_widget = self.input_fields[-1]

            for idx in self.content_layout.count():
                item = self.content_layout.itemAt(idx)
                if item.widget() is after_widget:
                    new_widget_index = idx
                    break
        child_entity = self.entity.add_new_key(key)
        widget = ModifiableDictItem(
            self.entity.collapsible, child_entity, self
        )
        self.input_fields.append(widget)
        self.content_layout.insertWidget(new_widget_index, widget)
        return widget

    def _on_entity_change(self):
        print("_on_entity_change", self.__class__.__name__, self.entity.path)


class ModifiableDict(QtWidgets.QWidget):
    def create_ui(self, label_widget=None):
        if self.hightlight_content:
            content_state = "hightlighted"
            bottom_margin = 5
        else:
            content_state = ""
            bottom_margin = 0

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        label = self.schema_data.get("label")

        if self.as_widget:
            body_widget = None
            self.label_widget = label_widget

        elif label is None:
            body_widget = None
            self.label_widget = None
        else:
            body_widget = ExpandingWidget(self.schema_data["label"], self)
            main_layout.addWidget(body_widget)

            self.label_widget = body_widget.label_widget

        self.body_widget = body_widget

        if body_widget is None:
            content_parent_widget = self
        else:
            content_parent_widget = body_widget

        content_widget = QtWidgets.QWidget(content_parent_widget)
        content_widget.setObjectName("ContentWidget")
        content_widget.setProperty("content_state", content_state)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, bottom_margin)

        if body_widget is None:
            main_layout.addWidget(content_widget)
        else:
            body_widget.set_content_widget(content_widget)

        self.body_widget = body_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

        if body_widget:
            collapsable = self.schema_data.get("collapsable", True)
            if collapsable:
                collapsed = self.schema_data.get("collapsed", True)
                if not collapsed:
                    body_widget.toggle_content()

            else:
                body_widget.hide_toolbox(hide_content=False)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        last_required_item = None
        for key in self.required_keys:
            last_required_item = self.add_row(key=key, is_required=True)

        if last_required_item:
            last_required_item.set_as_last_required()
        else:
            self.add_row(is_empty=True)

    def count(self):
        return len(self.input_fields)

    def set_value(self, value):
        self.validate_value(value)

        metadata = value.get(METADATA_KEY, {})
        dynamic_key_labels = metadata.get("dynamic_key_label") or {}

        required_items = list(self.required_inputs_by_key.values())
        previous_inputs = list()
        for input_field in self.input_fields:
            if input_field not in required_items:
                previous_inputs.append(input_field)

        for item_key, item_value in value.items():
            if item_key is METADATA_KEY:
                continue

            label = dynamic_key_labels.get(item_key)
            self.add_row(key=item_key, label=label, value=item_value)

        if self.collapsible_key:
            self.add_row(is_empty=True)

        for input_field in previous_inputs:
            self.remove_row(input_field)

        if self.count() == 0:
            self.add_row(is_empty=True)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        fields_by_keys = collections.defaultdict(list)
        for input_field in self.input_fields:
            key = input_field.key_value()
            fields_by_keys[key].append(input_field)

        for fields in fields_by_keys.values():
            if len(fields) == 1:
                field = fields[0]
                field.set_key_is_duplicated(False)
            else:
                for field in fields:
                    field.set_key_is_duplicated(True)

        if self.is_overidable:
            self._is_overriden = True
        else:
            self._has_studio_override = True

        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        elif self._has_studio_override:
            self._is_modified = self.item_value() != self.studio_value
        else:
            self._is_modified = self.item_value() != self.default_value

        self.update_style()

        self.value_changed.emit(self)

    @property
    def is_modified(self):
        is_modified = super(ModifiableDict, self).is_modified
        if is_modified:
            return is_modified

        for input_field in self.input_fields:
            if input_field.is_modified:
                return True
        return False

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def update_style(self):
        state = self._style_state()

        if self._state == state:
            return

        self._state = state

        if self.label_widget:
            self.label_widget.setProperty("state", state)
            self.label_widget.style().polish(self.label_widget)

        if not self.body_widget:
            return

        if state:
            child_state = "child-{}".format(state)
        else:
            child_state = ""

        self.body_widget.side_line_widget.setProperty("state", child_state)
        self.body_widget.side_line_widget.style().polish(
            self.body_widget.side_line_widget
        )

    def all_item_values(self):
        output = {}
        for item in self.input_fields:
            output.update(item.item_value())
        return output

    def item_value_with_metadata(self):
        if not self.collapsible_key:
            output = self.item_value()

        else:
            output = {}
            labels_by_key = {}
            for item in self.input_fields:
                labels_by_key[item.key_value()] = item.key_label_value()
                output.update(item.config_value())
            if METADATA_KEY not in output:
                output[METADATA_KEY] = {}
            output[METADATA_KEY]["dynamic_key_label"] = labels_by_key

        if self.value_is_env_group:
            for env_group_key, value in tuple(output.items()):
                env_keys = []
                for key in value.keys():
                    if key is not METADATA_KEY:
                        env_keys.append(key)

                if METADATA_KEY not in value:
                    value[METADATA_KEY] = {}

                value[METADATA_KEY]["environments"] = {env_group_key: env_keys}
                output[env_group_key] = value
        return output

    def item_value(self):
        output = {}
        for item in self.input_fields:
            output.update(item.config_value())
        return output

    def config_value(self):
        return {self.key: self.item_value_with_metadata()}

    def _create_item(self, row, key, is_empty, is_required):
        # Create new item
        item_widget = ModifiableDictItem(
            self.item_schema, self, self.content_widget
        )
        if is_empty:
            item_widget.set_as_empty()

        if is_required:
            item_widget.set_as_required(key)
            self.required_inputs_by_key[key] = item_widget

        item_widget.value_changed.connect(self._on_value_change)

        if row is None:
            self.content_layout.addWidget(item_widget)
            self.input_fields.append(item_widget)
        else:
            self.content_layout.insertWidget(row, item_widget)
            self.input_fields.insert(row, item_widget)

        previous_input = None
        if self.collapsible_key:
            for input_field in self.input_fields:
                if previous_input is not None:
                    self.setTabOrder(
                        previous_input, input_field.input_field
                    )
                previous_input = input_field.input_field.focusProxy()

        else:
            for input_field in self.input_fields:
                if previous_input is not None:
                    self.setTabOrder(
                        previous_input, input_field.key_input
                    )
                previous_input = input_field.input_field.focusProxy()
                self.setTabOrder(
                    input_field.key_input, previous_input
                )
        return item_widget

    def add_row(
        self,
        row=None,
        key=None,
        label=None,
        value=None,
        is_empty=False,
        is_required=False
    ):
        item_widget = self.required_inputs_by_key.get(key)
        if not item_widget:
            item_widget = self._create_item(row, key, is_empty, is_required)

        # Set value if entered value is not None
        # else (when add button clicked) trigger `_on_value_change`
        if value is not None and key is not None:
            if not self._has_studio_override:
                item_widget.update_default_values(key, label, value)
            elif self._is_overriden:
                item_widget.apply_overrides(key, label, value)
            else:
                item_widget.update_studio_values(key, label, value)
            self.hierarchical_style_update()
        else:
            self._on_value_change()
        self.parent().updateGeometry()

        return item_widget

    def remove_row(self, item_widget):
        item_widget.value_changed.disconnect()

        self.content_layout.removeWidget(item_widget)
        self.input_fields.remove(item_widget)
        item_widget.setParent(None)
        item_widget.deleteLater()

        if self.count() == 0:
            self.add_row(is_empty=True)

        self._on_value_change()
        self.parent().updateGeometry()

    @property
    def is_invalid(self):
        return self._is_invalid or self.child_invalid

    @property
    def child_invalid(self):
        for input_field in self.input_fields:
            if input_field.is_invalid:
                return True
        return False
