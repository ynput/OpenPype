from uuid import uuid4

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
        self.collapsible_key = entity_widget.entity.collapsible_key

        self.is_duplicated = False

        if self.collapsible_key:
            self.create_collapsible_ui()
        else:
            self.create_addible_ui()

    def add_new_item(self, key=None, label=None):
        input_field = self.entity_widget.add_new_key(key, label)
        if self.collapsible_key:
            self.key_input.setFocus(True)
        else:
            input_field.key_input.setFocus(True)
        return input_field

    def _on_add_clicked(self):
        self.add_new_item()

    def create_addible_ui(self):
        add_btn = create_add_btn(self)
        remove_btn = create_remove_btn(self)
        spacer_widget = SpacerWidget(self)

        remove_btn.setEnabled(False)

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

        if self.is_duplicated:
            return

        key = self.key_input.text()
        if key:
            label = self.key_label_input.text()
            self.key_input.clear()
            self.key_label_input.clear()
            self.add_new_item(key, label)

    def _on_key_change(self):
        key = self.key_input.text()
        self.is_duplicated = self.entity_widget.is_key_duplicated(key)
        key_input_state = ""
        if self.is_duplicated:
            key_input_state = "invalid"
        elif key != "":
            key_input_state = "modified"

        self.key_input.setProperty("state", key_input_state)
        self.key_input.style().polish(self.key_input)

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

        key_input.textChanged.connect(self._on_key_change)
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

        self.temp_key = ""
        self.uuid_key = None

        self._style_state = ""

        self.wrapper_widget = None

        if collapsible_key:
            self.create_collapsible_ui()
        else:
            self.create_addible_ui()
        self.update_style()

    @property
    def child_invalid(self):
        return self.is_key_duplicated or self.input_field.child_invalid

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

    def set_key(self, key):
        if self.uuid_key is not None and key == self.uuid_key:
            self.key_input.setText("")
        else:
            self.key_input.setText(key)

    def set_entity_value(self):
        self.input_field.set_entity_value()

    def set_is_key_duplicated(self, is_key_duplicated):
        if is_key_duplicated == self.is_key_duplicated:
            return

        self.is_key_duplicated = is_key_duplicated
        if self.collapsible_key:
            if is_key_duplicated:
                self.set_edit_mode(True)
            else:
                self._on_focus_lose()

        if not self.is_key_duplicated:
            self.entity_widget.change_key(self.key_value(), self)

        self.update_style()

    def set_key_label(self, key, label):
        self.set_key(key)
        if label:
            self.key_label_input.setText(label)
        self.set_edit_mode(False)

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
        if self.collapsible_key:
            self.set_edit_mode(False)

    def _on_key_label_change(self):
        self.update_key_label()

    def _on_key_change(self):
        key = self.key_value()
        is_key_duplicated = self.entity_widget.validate_key_duplication(
            self.temp_key, key, self
        )
        self.temp_key = key
        if is_key_duplicated:
            return

        if key:
            self.update_key_label()

        self.entity_widget.change_key(key, self)
        self.update_style()

    @property
    def value_is_env_group(self):
        return self.entity_widget.value_is_env_group

    def update_key_label(self):
        if not self.collapsible_key:
            return
        key_value = self.key_input.text()
        key_label_value = self.key_label_input.text()
        if key_label_value:
            label = "{} ({})".format(key_label_value, key_value)
        else:
            label = key_value
        self.wrapper_widget.label_widget.setText(label)

    def on_add_clicked(self):
        widget = self.entity_widget.add_new_key(None, None, self)
        widget.key_input.setFocus(True)

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
        self.entity_widget.remove_key(self)

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
        return self.is_key_duplicated or self.input_field.is_invalid

    def get_invalid(self):
        invalid = []
        if self.is_key_duplicated:
            invalid.append(self.key_input)
        invalid.extend(self.input_field.get_invalid())
        return invalid

    def update_style(self):
        key_input_state = ""
        if self.is_key_duplicated or self.key_value() == "":
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
        return self.entity_widget.input_fields.index(self)

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

    @property
    def child_invalid(self):
        for input_field in self.input_fields:
            if input_field.child_invalid:
                return True
        return False

    def get_invalid(self):
        invalid = []
        for input_field in self.input_fields:
            invalid.extend(input_field.get_invalid())
        return invalid

    def add_required_keys(self):
        # TODO implement
        pass

    def add_new_key(self, key, label=None, after_widget=None):
        uuid_key = None
        entity_key = key
        if not key:
            uuid_key = str(uuid4())
            entity_key = uuid_key

        child_entity = self.entity.add_new_key(entity_key)

        input_field = self.add_widget_for_child(child_entity, after_widget)
        if uuid_key:
            input_field.uuid_key = uuid_key

        if key:
            input_field.set_key_label(key, label)

        input_field.set_entity_value()

        self.on_shuffle()

        return input_field

    def remove_key(self, widget):
        key = self.entity.get_child_key(widget.entity)
        self.entity.pop(key)
        self.remove_row(widget)

    def change_key(self, new_key, widget):
        if not new_key or widget.is_key_duplicated:
            return

        child_obj = self.entity.get(new_key)
        # Skip if same key is already stored under the key
        if child_obj is widget.entity:
            return

        # Just change the key if not exist the same object
        if not child_obj:
            self.entity.change_child_key(widget.entity, new_key)
            return

        same_key_widget = None
        for input_field in self.input_fields:
            if input_field.entity is child_obj:
                same_key_widget = input_field
                break

        if not same_key_widget:
            # Would mean that child entity does not have input field in
            # this widget!
            raise KeyError("BUG: didn't find same key widget!")

        if same_key_widget.is_key_duplicated:
            return

        sk_new_key = same_key_widget.key_value()
        sk_old_key = self.entity.get_child_key(same_key_widget.entity)
        if sk_old_key != new_key:
            self.change_key(sk_new_key, same_key_widget)
            self.entity.change_child_key(widget.entity, new_key)
        else:
            # Swap entities if keys of each other are matching
            old_key = self.entity.get_child_key(widget.entity)
            (
                self.entity.children_by_key[new_key],
                self.entity.children_by_key[sk_new_key]
            ) = (
                self.entity.children_by_key[old_key],
                self.entity.children_by_key[sk_old_key]
            )

    def add_widget_for_child(
        self, child_entity, after_widget=None, first=False
    ):
        if first:
            new_widget_index = 0
        else:
            new_widget_index = len(self.input_fields)

        if self.input_fields and not first:
            if not after_widget:
                after_widget = self.input_fields[-1]

            for idx in range(self.content_layout.count()):
                item = self.content_layout.itemAt(idx)
                if item.widget() is after_widget:
                    new_widget_index = idx + 1
                    break

        input_field = ModifiableDictItem(
            self.entity.collapsible_key, child_entity, self
        )
        self.input_fields.append(input_field)
        self.content_layout.insertWidget(new_widget_index, input_field)
        return input_field

    def remove_row(self, widget):
        self.input_fields.remove(widget)
        self.content_layout.removeWidget(widget)
        widget.deleteLater()
        self.on_shuffle()

    def is_key_duplicated(self, key):
        """Method meant only for empty item to check duplicated keys."""
        for input_field in self.input_fields:
            item_key = input_field.key_value()
            if item_key == key:
                return True
        return False

    def validate_key_duplication(self, old_key, new_key, widget):
        old_key_items = []
        duplicated_items = []
        for input_field in self.input_fields:
            if input_field is widget:
                continue

            item_key = input_field.key_value()
            if item_key == new_key:
                duplicated_items.append(input_field)
            elif item_key == old_key:
                old_key_items.append(input_field)

        if duplicated_items:
            widget.set_is_key_duplicated(True)
            for input_field in duplicated_items:
                input_field.set_is_key_duplicated(True)
        else:
            widget.set_is_key_duplicated(False)

        if len(old_key_items) == 1:
            for input_field in old_key_items:
                input_field.set_is_key_duplicated(False)
        return bool(duplicated_items)

    def on_shuffle(self):
        if not self.entity.collapsible_key:
            self.empty_row.setVisible(len(self.input_fields) == 0)
        self.update_style()

    def _on_entity_change(self):
        current_input_fields = []
        for input_field in self.input_fields:
            current_input_fields.append(input_field)

        for key, child_entity in self.entity.items():
            found_idx = None
            previous_input = None
            for idx, input_field in enumerate(current_input_fields):
                if input_field.entity is not child_entity:
                    previous_input = input_field
                else:
                    found_idx = idx
                    break

            if found_idx is None:
                args = [previous_input]
                if previous_input is None:
                    args.append(True)

                _input_field = self.add_widget_for_child(child_entity, *args)
                _input_field.origin_key = key
                _input_field.set_key(key)
                _input_field.set_entity_value()

            else:
                current_input_fields.pop(found_idx)
                if input_field.key_value() != key:
                    input_field.set_key(key)

        for input_field in current_input_fields:
            self.remove_row(input_field)

    def set_entity_value(self):
        for input_field in tuple(self.input_fields):
            self.remove_row(input_field)

        for key, child_entity in self.entity.items():
            input_field = self.add_widget_for_child(child_entity)
            input_field.origin_key = key
            input_field.set_key(key)
            input_field.set_entity_value()
        self.on_shuffle()

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def update_style(self):
        _style_state = self.get_style_state(
            self.is_invalid,
            self.entity.has_unsaved_changes,
            self.entity.has_project_override,
            self.entity.has_studio_override
        )

        if self._style_state == _style_state:
            return

        self._style_state = _style_state

        if self.label_widget:
            self.label_widget.setProperty("state", _style_state)
            self.label_widget.style().polish(self.label_widget)

        if not self.body_widget:
            return

        if _style_state:
            child_state = "child-{}".format(_style_state)
        else:
            child_state = ""

        self.body_widget.side_line_widget.setProperty("state", child_state)
        self.body_widget.side_line_widget.style().polish(
            self.body_widget.side_line_widget
        )
