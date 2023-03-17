from qtpy import QtWidgets, QtCore, QtGui

from .item_widgets import InputWidget

from openpype.widgets.color_widgets import (
    ColorPickerWidget,
    draw_checkerboard_tile
)


class ColorWidget(InputWidget):
    def _add_inputs_to_layout(self):
        self.input_field = ColorViewer(self.content_widget)

        self.setFocusProxy(self.input_field)

        self.content_layout.addWidget(self.input_field, 1)

        self.input_field.clicked.connect(self._on_click)

        self._dialog = None

    def _on_click(self):
        if self._dialog:
            self._dialog.open()
            return

        dialog = ColorDialog(
            self.input_field.color(), self.entity.use_alpha, self
        )
        self._dialog = dialog

        dialog.open()
        dialog.finished.connect(self._on_dialog_finish)

    def _on_dialog_finish(self, *_args):
        if not self._dialog:
            return

        color = self._dialog.result()
        if color is not None:
            self.input_field.set_color(color)
            self._on_value_change()

        self._dialog.deleteLater()
        self._dialog = None

    def _on_entity_change(self):
        if self.entity.value != self.input_value():
            self.set_entity_value()

    def set_entity_value(self):
        self.input_field.set_color(*self.entity.value)

    def input_value(self):
        color = self.input_field.color()
        return [color.red(), color.green(), color.blue(), color.alpha()]

    def _on_value_change(self):
        if self.ignore_input_changes:
            return

        self.entity.set(self.input_value())


class ColorViewer(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super(ColorViewer, self).__init__(parent)

        self.setMinimumSize(10, 10)

        self.actual_pen = QtGui.QPen()
        self.actual_color = QtGui.QColor()
        self._checkerboard = None

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super(ColorViewer, self).mouseReleaseEvent(event)

    def checkerboard(self):
        if not self._checkerboard:
            self._checkerboard = draw_checkerboard_tile(self.height() / 4)
        return self._checkerboard

    def color(self):
        return self.actual_color

    def set_color(self, *args):
        # Create copy of entered color
        self.actual_color = QtGui.QColor(*args)
        # Repaint
        self.update()

    def set_alpha(self, alpha):
        # Change alpha of current color
        self.actual_color.setAlpha(alpha)
        # Repaint
        self.update()

    def paintEvent(self, event):
        rect = event.rect()

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        radius = rect.height() / 2
        rounded_rect = QtGui.QPainterPath()
        rounded_rect.addRoundedRect(QtCore.QRectF(rect), radius, radius)
        painter.setClipPath(rounded_rect)

        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 67))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawTiledPixmap(rect, self.checkerboard())
        painter.fillRect(rect, self.actual_color)
        painter.drawPath(rounded_rect)

        painter.end()


class ColorDialog(QtWidgets.QDialog):
    def __init__(self, color=None, use_alpha=True, parent=None):
        super(ColorDialog, self).__init__(parent)

        self.setWindowTitle("Color picker dialog")

        picker_widget = ColorPickerWidget(color, use_alpha, self)

        footer_widget = QtWidgets.QWidget(self)

        ok_btn = QtWidgets.QPushButton("Ok", footer_widget)
        cancel_btn = QtWidgets.QPushButton("Cancel", footer_widget)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(ok_btn)
        footer_layout.addWidget(cancel_btn)

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(picker_widget, 1)
        layout.addWidget(footer_widget, 0)

        ok_btn.clicked.connect(self.on_ok_clicked)
        cancel_btn.clicked.connect(self.on_cancel_clicked)

        self.picker_widget = picker_widget
        self.ok_btn = ok_btn
        self.cancel_btn = cancel_btn

        self._result = None

    def showEvent(self, event):
        super(ColorDialog, self).showEvent(event)

        btns_width = max(self.ok_btn.width(), self.cancel_btn.width())
        self.ok_btn.setFixedWidth(btns_width)
        self.cancel_btn.setFixedWidth(btns_width)

    def on_ok_clicked(self):
        self._result = self.picker_widget.color()
        self.close()

    def on_cancel_clicked(self):
        self._result = None
        self.close()

    def result(self):
        return self._result
