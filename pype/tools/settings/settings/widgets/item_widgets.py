import json

from Qt import QtWidgets, QtCore, QtGui

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
from .base import (
    BaseWidget,
    InputWidget,
    GUIWidget
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
from .base import (
    BaseWidget,
    InputWidget
)
from .list_item_widget import ListWidget
from .lib import CHILD_OFFSET


class DictImmutableKeysWidget(BaseWidget):
    def create_ui(self):
        self.input_fields = []

        if not self.entity.is_dynamic_item and not self.entity.label:
            self._ui_item_without_label()

        else:
            self._ui_item_or_as_widget()

        for child_obj in self.entity.children:
            self.input_fields.append(
                self.create_ui_for_entity(child_obj, self)
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


class DictMutableKeysWidget(BaseWidget):
    pass


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

        self.input_field = self.create_ui_for_entity(
            self.entity.child_obj, self
        )

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


