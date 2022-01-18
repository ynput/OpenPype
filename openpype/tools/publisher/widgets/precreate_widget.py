from Qt import QtWidgets

from openpype.widgets.attribute_defs import create_widget_for_attr_def


class AttributesWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(AttributesWidget, self).__init__(parent)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._layout = layout

        self._widgets = []

    def current_value(self):
        output = {}
        for widget in self._widgets:
            attr_def = widget.attr_def
            if attr_def.is_value_def:
                output[attr_def.key] = widget.current_value()
        return output

    def clear_attr_defs(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setVisible(False)
                widget.deleteLater()

        self._widgets = []

    def set_attr_defs(self, attr_defs):
        self.clear_attr_defs()

        row = 0
        for attr_def in attr_defs:
            widget = create_widget_for_attr_def(attr_def, self)

            expand_cols = 2
            if attr_def.is_value_def and attr_def.is_label_horizontal:
                expand_cols = 1

            col_num = 2 - expand_cols

            if attr_def.label:
                label_widget = QtWidgets.QLabel(attr_def.label, self)
                self._layout.addWidget(
                    label_widget, row, 0, 1, expand_cols
                )
                if not attr_def.is_label_horizontal:
                    row += 1

            self._layout.addWidget(
                widget, row, col_num, 1, expand_cols
            )
            self._widgets.append(widget)

            row += 1
