import json

from Qt import QtWidgets, QtCore, QtGui
from avalon.vendor import qtawesome
from pype.settings.entities import (
    GUIEntity,
    DictImmutableKeysEntity,
    DictMutableKeysEntity,
    ListEntity,
    PathEntity,
    ListStrictEntity,

    NumberEntity,
    BoolEntity,
    EnumEntity,
    TextEntity,
    PathInput,
    RawJsonEntity
)
from .widgets import (
    IconButton,
    ExpandingWidget,
    NumberSpinBox,
    GridLabelWidget,
    ComboBox,
    NiceCheckbox
)
from .multiselection_combobox import MultiSelectionComboBox
from .lib import CHILD_OFFSET

BTN_FIXED_SIZE = 20


class BaseWidget(QtWidgets.QWidget):
    def __init__(self, entity, entity_widget):
        self.entity = entity
        self.entity_widget = entity_widget

        self.ignore_input_changes = entity_widget.ignore_input_changes

        self._style_state = None

        super(BaseWidget, self).__init__(entity_widget.content_widget)

        self.entity.on_change_callbacks.append(self._on_entity_change)

        self.label_widget = None
        self.create_ui()

    @staticmethod
    def get_style_state(
        is_invalid, is_modified, has_project_override, has_studio_override
    ):
        """Return stylesheet state by intered booleans."""
        if is_invalid:
            return "invalid"
        if is_modified:
            return "modified"
        if has_project_override:
            return "overriden"
        if has_studio_override:
            return "studio"
        return ""

    def show_actions_menu(self, event):
        print("Show actions for {}".format(self.entity.path))


class InputWidget(BaseWidget):
    def update_style(self):
        state = self.get_style_state(
            self.entity.is_invalid,
            self.entity.has_unsaved_changes,
            self.entity.has_project_override,
            self.entity.has_studio_override
        )
        if self._style_state == state:
            return

        self._style_state = state

        self.input_field.setProperty("input-state", state)
        self.input_field.style().polish(self.input_field)
        if self.label_widget:
            self.label_widget.setProperty("state", state)
            self.label_widget.style().polish(self.label_widget)


class GUIWidget(BaseWidget):
    separator_height = 2

    def create_ui(self):
        entity_type = self.entity["type"]
        if entity_type == "label":
            self._create_label_ui()
        elif entity_type in ("separator", "splitter"):
            self._create_separator_ui()
        else:
            raise KeyError("Unknown GUI type {}".format(entity_type))

        self.entity_widget.add_widget_to_layout(self)

    def _create_label_ui(self):
        self.setObjectName("LabelWidget")

        label = self.entity["label"]
        label_widget = QtWidgets.QLabel(label, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.addWidget(label_widget)

    def _create_separator_ui(self):
        splitter_item = QtWidgets.QWidget(self)
        splitter_item.setObjectName("SplitterItem")
        splitter_item.setMinimumHeight(self.separator_height)
        splitter_item.setMaximumHeight(self.separator_height)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(splitter_item)

    def _on_entity_change(self):
        pass


class DictImmutableKeysWidget(BaseWidget):
    def create_ui(self):
        self.input_fields = []

        if not self.entity.is_dynamic_item and not self.entity.label:
            self._ui_item_without_label()

        else:
            self._ui_item_or_as_widget()

        for child_obj in self.entity.children:
            self.input_fields.append(
                create_ui_for_entity(child_obj, self)
            )

        self.entity_widget.add_widget_to_layout(self)

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
            show_borders = str(int(self.show_borders))
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
        row = self.content_layout.rowCount()
        if label:
            label_widget = GridLabelWidget(label, widget)
            label_widget.input_field = widget
            widget.label_widget = label_widget
            self.content_layout.addWidget(label_widget, row, 0, 1, 1)
            self.content_layout.addWidget(widget, row, 1, 1, 1)
        else:
            self.content_layout.addWidget(widget, row, 0, 1, 2)

    def _on_entity_change(self):
        print("_on_entity_change", self.__class__.__name__, self.entity.path)


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

    def _on_value_change(self):
        if self.ignore_input_changes:
            return
        print("_on_value_change", self.__class__.__name__, self.entity.path)

    def _on_entity_change(self):
        self.update_style()


class TextWidget(InputWidget):
    def create_ui(self):
        multiline = self.entity.multiline
        if multiline:
            self.input_field = QtWidgets.QPlainTextEdit(self)
        else:
            self.input_field = QtWidgets.QLineEdit(self)

        self.set_value(self.entity.value)

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

    def set_value(self, text):
        if self.entity.multiline:
            self.input_field.setPlainText(text)
        else:
            self.input_field.setText(text)

    def input_value(self):
        if self.entity.multiline:
            return self.input_field.toPlainText()
        else:
            return self.input_field.text()

    def _on_value_change(self):
        if self.ignore_input_changes:
            return

        text = self.input_value()
        self.entity.set_value(text)

    def _on_entity_change(self):
        self.update_style()


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
        self.input_field.setValue(self.entity.value)

        self.setFocusProxy(self.input_field)

        layout.addWidget(self.input_field, 1)

        self.input_field.valueChanged.connect(self._on_value_change)

        self.entity_widget.add_widget_to_layout(self, self.entity.label)

    def _on_value_change(self):
        if self.ignore_input_changes:
            return
        self.entity.set_value(self.input_field.value())

    def _on_entity_change(self):
        self.update_style()


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

        self.input_field.set_value(self.entity.value)

        self.setFocusProxy(self.input_field)

        layout.addWidget(self.input_field, 1, alignment=QtCore.Qt.AlignTop)

        self.input_field.textChanged.connect(self._on_value_change)
        self.entity_widget.add_widget_to_layout(self, self.entity.label)

    def _on_entity_change(self):
        self.update_style()

    def _on_value_change(self):
        self.update_style()
        print("_on_value_change", self.__class__.__name__, self.entity.path)


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

    def _on_value_change(self):
        if self.ignore_input_changes:
            return
        print("_on_value_change", self.__class__.__name__, self.entity.path)

    def _on_entity_change(self):
        self.update_style()


class PathWidget(BaseWidget):
    def create_ui(self):
        self.content_widget = self
        self.content_layout = QtWidgets.QGridLayout(self)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)

        self.input_field = create_ui_for_entity(self.entity.child_obj, self)

        self.entity_widget.add_widget_to_layout(self, self.entity.label)

    def _on_entity_change(self):
        print("_on_entity_change", self.__class__.__name__, self.entity.path)

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

    def _on_value_change(self):
        print("_on_value_change", self.__class__.__name__, self.entity.path)

    def _on_entity_change(self):
        print("_on_entity_change", self.__class__.__name__, self.entity.path)


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

        self.input_field = create_ui_for_entity(self.entity, self)

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

    def add_widget_to_layout(self, widget, label=None):
        self.content_layout.addWidget(widget, 1)

    def row(self):
        return self.entity_widget.input_fields.index(self)

    def parent_rows_count(self):
        return len(self.entity_widget.input_fields)

    def _on_add_clicked(self):
        self.entity_widget.add_row(row=self.row() + 1)

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


class ListWidget(InputWidget):
    def create_ui(self):
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

        self.update_value()

    def _on_value_change(self):
        print("_on_value_change", self.__class__.__name__, self.entity.path)

    def _on_entity_change(self):
        print("_on_entity_change", self.__class__.__name__, self.entity.path)

    def count(self):
        return len(self.input_fields)

    def update_value(self):
        for input_field in tuple(self.input_fields):
            self.remove_row(input_field)

        for entity in self.entity.children:
            self.add_row(entity)

        self.empty_row.setVisible(self.count() == 0)

    def swap_rows(self, row_1, row_2):
        if row_1 == row_2:
            return

        if row_1 > row_2:
            row_1, row_2 = row_2, row_1

        field_1 = self.input_fields[row_1]
        field_2 = self.input_fields[row_2]

        self.input_fields[row_1] = field_2
        self.input_fields[row_2] = field_1

        layout_index = self.inputs_layout.indexOf(field_1)
        self.inputs_layout.insertWidget(layout_index + 1, field_1)

        field_1.order_changed()
        field_2.order_changed()

    def add_new_item(self, row=None):
        child_entity = self.entity.add_new_item()
        self.add_row(child_entity)

    def add_row(self, child_entity, row=None):
        # Create new item
        item_widget = ListItem(child_entity, self)

        previous_field = None
        next_field = None

        if row is None:
            if self.input_fields:
                previous_field = self.input_fields[-1]
            self.inputs_layout.addWidget(item_widget)
            self.input_fields.append(item_widget)
        else:
            if row > 0:
                previous_field = self.input_fields[row - 1]

            max_index = self.count()
            if row < max_index:
                next_field = self.input_fields[row]

            self.inputs_layout.insertWidget(row, item_widget)
            self.input_fields.insert(row, item_widget)

        if previous_field:
            previous_field.order_changed()

        if next_field:
            next_field.order_changed()

        item_widget.value_changed.connect(self._on_value_change)

        item_widget.order_changed()

        previous_input = None
        for input_field in self.input_fields:
            if previous_input is not None:
                self.setTabOrder(
                    previous_input, input_field.value_input.focusProxy()
                )
            previous_input = input_field.value_input.focusProxy()

        self.updateGeometry()

    def remove_row(self, item_widget):
        row = self.input_fields.index(item_widget)
        previous_field = None
        next_field = None
        if row > 0:
            previous_field = self.input_fields[row - 1]

        if row != len(self.input_fields) - 1:
            next_field = self.input_fields[row + 1]

        self.inputs_layout.removeWidget(item_widget)
        self.input_fields.pop(row)
        item_widget.setParent(None)
        item_widget.deleteLater()

        if previous_field:
            previous_field.order_changed()

        if next_field:
            next_field.order_changed()

        self.empty_row.setVisible(self.count() == 0)

        self.updateGeometry()


def create_ui_for_entity(entity, entity_widget):
    if isinstance(entity, GUIEntity):
        return GUIWidget(entity, entity_widget)

    elif isinstance(entity, DictImmutableKeysEntity):
        return DictImmutableKeysWidget(entity, entity_widget)

    elif isinstance(entity, BoolEntity):
        return BoolWidget(entity, entity_widget)

    elif isinstance(entity, TextEntity):
        return TextWidget(entity, entity_widget)

    elif isinstance(entity, NumberEntity):
        return NumberWidget(entity, entity_widget)

    elif isinstance(entity, RawJsonEntity):
        return RawJsonWidget(entity, entity_widget)

    elif isinstance(entity, EnumEntity):
        return EnumeratorWidget(entity, entity_widget)

    elif isinstance(entity, PathEntity):
        return PathWidget(entity, entity_widget)

    elif isinstance(entity, PathInput):
        return PathInputWidget(entity, entity_widget)

    elif isinstance(entity, ListEntity):
        return ListWidget(entity, entity_widget)

    # DictMutableKeysEntity,
    # ListStrictEntity,
    label = "<{}>: {} ({})".format(
        entity.__class__.__name__, entity.path, entity.value
    )
    widget = QtWidgets.QLabel(label, entity_widget)
    entity_widget.add_widget_to_layout(widget)
    return widget
