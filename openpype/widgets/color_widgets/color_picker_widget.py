import os
from Qt import QtWidgets, QtCore, QtGui

from .color_triangle import QtColorTriangle
from .color_view import ColorViewer
from .color_screen_pick import PickScreenColorWidget
from .color_inputs import (
    ColorInputsWidget,
    AlphaSlider,
    AlphaInputs,
    HEXInputs,
    RGBInputs,
    HSLInputs,
    HSVInputs,
    CMYKInputs
)


class ColorPickerWidget(QtWidgets.QWidget):
    color_changed = QtCore.Signal(QtGui.QColor)

    def __init__(self, color=None, parent=None):
        super(ColorPickerWidget, self).__init__(parent)

        top_part = QtWidgets.QWidget(self)
        left_side = QtWidgets.QWidget(top_part)

        # Color triangle
        color_triangle = QtColorTriangle(left_side)

        alpha_slider_proxy = QtWidgets.QWidget(left_side)
        alpha_slider = AlphaSlider(QtCore.Qt.Horizontal, alpha_slider_proxy)

        alpha_slider_layout = QtWidgets.QHBoxLayout(alpha_slider_proxy)
        alpha_slider_layout.setContentsMargins(5, 5, 5, 5)
        alpha_slider_layout.addWidget(alpha_slider, 1)

        left_layout = QtWidgets.QVBoxLayout(left_side)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(color_triangle)
        left_layout.addWidget(alpha_slider)

        right_side = QtWidgets.QWidget(top_part)

        # Eye picked widget
        pick_widget = PickScreenColorWidget()
        pick_widget.setMaximumHeight(50)

        # Color pick button
        btn_pick_color = QtWidgets.QPushButton(right_side)
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "eyedropper.png"
        )
        btn_pick_color.setIcon(QtGui.QIcon(icon_path))
        btn_pick_color.setToolTip("Pick a color")

        # Color preview
        color_view = ColorViewer(right_side)
        color_view.setMaximumHeight(50)

        row = 0
        right_layout = QtWidgets.QGridLayout(right_side)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(btn_pick_color, row, 0)
        right_layout.addWidget(color_view, row, 1)

        color_inputs_color = QtGui.QColor()
        col_inputs_by_label = [
            ("HEX", HEXInputs(color_inputs_color, right_side)),
            ("RGB", RGBInputs(color_inputs_color, right_side)),
            ("HSL", HSLInputs(color_inputs_color, right_side)),
            ("HSV", HSVInputs(color_inputs_color, right_side))
        ]
        color_input_fields = []
        for label, input_field in col_inputs_by_label:
            row += 1
            right_layout.addWidget(QtWidgets.QLabel(label, right_side), row, 0)
            right_layout.addWidget(input_field, row, 1)
            input_field.value_changed.connect(
                self._on_color_input_value_change
            )
            color_input_fields.append(input_field)

        row += 1
        alpha_inputs = AlphaInputs(right_side)
        right_layout.addWidget(QtWidgets.QLabel("Alpha", right_side), row, 0)
        right_layout.addWidget(alpha_inputs, row, 1)

        row += 1
        right_layout.setRowStretch(row, 1)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(5)
        layout.addWidget(left_side, 1)
        layout.addWidget(right_side, 0)

        color_view.set_color(color_triangle.cur_color)

        color_triangle.color_changed.connect(self.triangle_color_changed)
        alpha_slider.valueChanged.connect(self._on_alpha_slider_change)
        pick_widget.color_selected.connect(self.on_color_change)
        alpha_inputs.alpha_changed.connect(self._on_alpha_inputs_changed)
        btn_pick_color.released.connect(self.pick_color)

        self.color_input_fields = color_input_fields
        self.color_inputs_color = color_inputs_color

        self.pick_widget = pick_widget

        self.color_triangle = color_triangle
        self.alpha_slider = alpha_slider

        self.color_view = color_view
        self.alpha_inputs = alpha_inputs
        self.btn_pick_color = btn_pick_color

        self._minimum_size_set = False

        if color:
            self.set_color(color)
            self.alpha_changed(color.alpha())

    def showEvent(self, event):
        super(ColorPickerWidget, self).showEvent(event)
        if self._minimum_size_set:
            return

        triangle_size = max(int(self.width() / 5 * 3), 180)
        self.color_triangle.setMinimumWidth(triangle_size)
        self.color_triangle.setMinimumHeight(triangle_size)
        self._minimum_size_set = True

    def color(self):
        return self.color_view.color()

    def set_color(self, color):
        self.alpha_inputs.set_alpha(color.alpha())
        self.on_color_change(color)

    def pick_color(self):
        self.pick_widget.pick_color()

    def triangle_color_changed(self, color):
        self.color_view.set_color(color)
        if self.color_inputs_color != color:
            self.color_inputs_color.setRgb(
                color.red(), color.green(), color.blue()
            )
            for color_input in self.color_input_fields:
                color_input.color_changed()

    def on_color_change(self, color):
        self.color_view.set_color(color)
        self.color_triangle.set_color(color)
        if self.color_inputs_color != color:
            self.color_inputs_color.setRgb(
                color.red(), color.green(), color.blue()
            )
            for color_input in self.color_input_fields:
                color_input.color_changed()

    def _on_color_input_value_change(self):
        for input_field in self.color_input_fields:
            input_field.color_changed()
        self.on_color_change(QtGui.QColor(self.color_inputs_color))

    def alpha_changed(self, value):
        self.color_view.set_alpha(value)
        if self.alpha_slider.value() != value:
            self.alpha_slider.setValue(value)

        if self.alpha_inputs.alpha_value != value:
            self.alpha_inputs.set_alpha(value)

    def _on_alpha_inputs_changed(self, value):
        self.alpha_changed(value)

    def _on_alpha_slider_change(self, value):
        self.alpha_changed(value)
