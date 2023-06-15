# -*- coding: utf-8 -*-

from qtpy import QtWidgets, QtCore, QtGui

from openpype.style import get_objected_colors


class _VLineWidget(QtWidgets.QWidget):
    """Widget drawing 1px wide vertical line.

    ```  │  ```

    Line is drawn in the middle of widget.

    It is expected that parent widget will set width.
    """
    def __init__(self, color, line_size, left, parent):
        super(_VLineWidget, self).__init__(parent)
        self._color = color
        self._left = left
        self._line_size = line_size

    def set_line_size(self, line_size):
        self._line_size = line_size

    def paintEvent(self, event):
        if not self.isVisible():
            return

        pos_x = self._line_size * 0.5
        if not self._left:
            pos_x = self.width() - pos_x

        painter = QtGui.QPainter(self)
        painter.setRenderHints(
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.SmoothPixmapTransform
        )

        if self._color:
            pen = QtGui.QPen(self._color)
        else:
            pen = painter.pen()
        pen.setWidth(self._line_size)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.transparent)
        painter.drawRect(
            QtCore.QRectF(
                pos_x,
                -self._line_size,
                pos_x + (self.width() * 2),
                self.height() + (self._line_size * 2)
            )
        )
        painter.end()


class _HBottomLineWidget(QtWidgets.QWidget):
    """Widget drawing 1px wide vertical line with side lines going upwards.

    ```└─────────────┘```

    Corners may have curve set by radius (`set_radius`). Radius should expect
    height of widget.

    Bottom line is drawn at the bottom of widget. If radius is 0 then height
    of widget should be 1px.

    It is expected that parent widget will set height and radius.
    """
    def __init__(self, color, line_size, parent):
        super(_HBottomLineWidget, self).__init__(parent)
        self._color = color
        self._radius = 0
        self._line_size = line_size

    def set_radius(self, radius):
        self._radius = radius

    def set_line_size(self, line_size):
        self._line_size = line_size

    def paintEvent(self, event):
        if not self.isVisible():
            return

        x_offset = self._line_size * 0.5
        rect = QtCore.QRectF(
            x_offset,
            -self._radius,
            self.width() - (2 * x_offset),
            (self.height() + self._radius) - x_offset
        )
        painter = QtGui.QPainter(self)
        painter.setRenderHints(
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.SmoothPixmapTransform
        )

        if self._color:
            pen = QtGui.QPen(self._color)
        else:
            pen = painter.pen()
        pen.setWidth(self._line_size)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.transparent)
        if self._radius:
            painter.drawRoundedRect(rect, self._radius, self._radius)
        else:
            painter.drawRect(rect)
        painter.end()


class _HTopCornerLineWidget(QtWidgets.QWidget):
    """Widget drawing 1px wide horizontal line with side line going downwards.

    ```────────┐```
          or
    ```┌───────```

    Horizontal line is drawn in the middle of widget.

    Widget represents left or right corner. Corner may have curve set by
    radius (`set_radius`). Radius should expect height of widget (maximum half
    height of widget).

    It is expected that parent widget will set height and radius.
    """

    def __init__(self, color, line_size, left_side, parent):
        super(_HTopCornerLineWidget, self).__init__(parent)
        self._left_side = left_side
        self._line_size = line_size
        self._color = color
        self._radius = 0

    def set_radius(self, radius):
        self._radius = radius

    def set_line_size(self, line_size):
        self._line_size = line_size

    def paintEvent(self, event):
        if not self.isVisible():
            return

        pos_y = self.height() * 0.5
        x_offset = self._line_size * 0.5
        if self._left_side:
            rect = QtCore.QRectF(
                x_offset,
                pos_y,
                self.width() + self._radius + x_offset,
                self.height()
            )
        else:
            rect = QtCore.QRectF(
                (-self._radius),
                pos_y,
                (self.width() + self._radius) - x_offset,
                self.height()
            )

        painter = QtGui.QPainter(self)
        painter.setRenderHints(
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.SmoothPixmapTransform
        )
        if self._color:
            pen = QtGui.QPen(self._color)
        else:
            pen = painter.pen()
        pen.setWidth(self._line_size)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.transparent)
        if self._radius:
            painter.drawRoundedRect(rect, self._radius, self._radius)
        else:
            painter.drawRect(rect)
        painter.end()


class BorderedLabelWidget(QtWidgets.QFrame):
    """Draws borders around widget with label in the middle of top.

    ┌─────── Label ────────┐
    │                      │
    │                      │
    │       CONTENT        │
    │                      │
    │                      │
    └──────────────────────┘
    """
    def __init__(self, label, parent):
        super(BorderedLabelWidget, self).__init__(parent)
        color_value = get_objected_colors("border")
        color = None
        if color_value:
            color = color_value.get_qcolor()

        line_size = 1

        top_left_w = _HTopCornerLineWidget(color, line_size, True, self)
        top_right_w = _HTopCornerLineWidget(color, line_size, False, self)

        label_widget = QtWidgets.QLabel(label, self)

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(5)
        top_layout.addWidget(top_left_w, 1)
        top_layout.addWidget(label_widget, 0)
        top_layout.addWidget(top_right_w, 1)

        left_w = _VLineWidget(color, line_size, True, self)
        right_w = _VLineWidget(color, line_size, False, self)

        bottom_w = _HBottomLineWidget(color, line_size, self)

        center_layout = QtWidgets.QHBoxLayout()
        center_layout.setContentsMargins(5, 5, 5, 5)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addLayout(top_layout, 0, 0, 1, 3)

        layout.addWidget(left_w, 1, 0)
        layout.addLayout(center_layout, 1, 1)
        layout.addWidget(right_w, 1, 2)

        layout.addWidget(bottom_w, 2, 0, 1, 3)

        layout.setColumnStretch(1, 1)
        layout.setRowStretch(1, 1)

        self._widget = None

        self._radius = 0
        self._line_size = line_size

        self._top_left_w = top_left_w
        self._top_right_w = top_right_w
        self._left_w = left_w
        self._right_w = right_w
        self._bottom_w = bottom_w
        self._label_widget = label_widget
        self._center_layout = center_layout

    def set_content_margins(self, value):
        """Set margins around content."""
        self._center_layout.setContentsMargins(
            value, value, value, value
        )

    def set_line_size(self, line_size):
        if self._line_size == line_size:
            return
        self._line_size = line_size
        for widget in (
            self._top_left_w,
            self._top_right_w,
            self._left_w,
            self._right_w,
            self._bottom_w
        ):
            widget.set_line_size(line_size)
        self._recalculate_sizes()

    def showEvent(self, event):
        super(BorderedLabelWidget, self).showEvent(event)
        self._recalculate_sizes()

    def _recalculate_sizes(self):
        height = self._label_widget.height()
        radius = int((height + (height % 2)) / 2)
        self._radius = radius

        radius_size = self._line_size + 1
        if radius_size < radius:
            radius_size = radius

        if radius:
            side_width = self._line_size + radius
        else:
            side_width = self._line_size + 1

        # Don't use fixed width/height as that would set also set
        #   the other size (When fixed width is set then is also set
        #   fixed height).
        self._left_w.setMinimumWidth(side_width)
        self._left_w.setMaximumWidth(side_width)
        self._right_w.setMinimumWidth(side_width)
        self._right_w.setMaximumWidth(side_width)
        self._bottom_w.setMinimumHeight(radius_size)
        self._bottom_w.setMaximumHeight(radius_size)
        self._bottom_w.set_radius(radius)
        self._top_right_w.set_radius(radius)
        self._top_left_w.set_radius(radius)
        if self._widget:
            self._widget.update()

    def set_center_widget(self, widget):
        """Set content widget and add it to center."""
        while self._center_layout.count():
            item = self._center_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._widget = widget
        if isinstance(widget, QtWidgets.QLayout):
            self._center_layout.addLayout(widget)
        else:
            self._center_layout.addWidget(widget)
