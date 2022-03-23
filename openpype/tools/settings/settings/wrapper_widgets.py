from uuid import uuid4
from Qt import QtWidgets

from .widgets import (
    ExpandingWidget,
    GridLabelWidget
)
from openpype.tools.settings import CHILD_OFFSET


class WrapperWidget(QtWidgets.QWidget):
    def __init__(self, schema_data, parent=None):
        super(WrapperWidget, self).__init__(parent)

        self.entity = None
        self.id = uuid4()
        self.schema_data = schema_data
        self.input_fields = []

        self.create_ui()

    def make_sure_is_visible(self, *args, **kwargs):
        changed = False
        for input_field in self.input_fields:
            if input_field.make_sure_is_visible(*args, **kwargs):
                changed = True
                break
        return changed

    def create_ui(self):
        raise NotImplementedError(
            "{} does not have implemented `create_ui`.".format(
                self.__class__.__name__
            )
        )

    def add_widget_to_layout(self, widget, label=None):
        raise NotImplementedError(
            "{} does not have implemented `add_widget_to_layout`.".format(
                self.__class__.__name__
            )
        )


class FormWrapper(WrapperWidget):
    def create_ui(self):
        self.content_layout = QtWidgets.QFormLayout(self)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

    def add_widget_to_layout(self, widget, label=None):
        if isinstance(widget, WrapperWidget):
            raise TypeError(
                "FormWrapper can't have other wrappers as children."
            )

        self.input_fields.append(widget)

        label_widget = GridLabelWidget(label, widget)
        label_widget.input_field = widget
        widget.label_widget = label_widget

        self.content_layout.addRow(label_widget, widget)


class CollapsibleWrapper(WrapperWidget):
    def create_ui(self):
        self.collapsible = self.schema_data.get("collapsible", True)
        self.collapsed = self.schema_data.get("collapsed", True)

        content_widget = QtWidgets.QWidget(self)
        content_widget.setObjectName("ContentWidget")
        content_widget.setProperty("content_state", "")

        content_layout = QtWidgets.QGridLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)

        body_widget = ExpandingWidget(self.schema_data["label"], self)
        body_widget.set_content_widget(content_widget)

        label_widget = body_widget.label_widget

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        if not body_widget:
            main_layout.addWidget(content_widget)
        else:
            main_layout.addWidget(body_widget)

        self.label_widget = label_widget
        self.body_widget = body_widget
        self.content_layout = content_layout

        if self.collapsible:
            if not self.entity.collapsed:
                body_widget.toggle_content()
        else:
            body_widget.hide_toolbox(hide_content=False)

    def make_sure_is_visible(self, *args, **kwargs):
        result = super(CollapsibleWrapper, self).make_sure_is_visible(
            *args, **kwargs
        )
        if result:
            self.body_widget.toggle_content(True)
        return result

    def add_widget_to_layout(self, widget, label=None):
        self.input_fields.append(widget)

        row = self.content_layout.rowCount()

        if not label or isinstance(widget, WrapperWidget):
            self.content_layout.addWidget(widget, row, 0, 1, 2)

        else:
            label_widget = GridLabelWidget(label, widget)
            label_widget.input_field = widget
            widget.label_widget = label_widget
            self.content_layout.addWidget(label_widget, row, 0, 1, 1)
            self.content_layout.addWidget(widget, row, 1, 1, 1)
