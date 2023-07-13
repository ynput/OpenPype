from qtpy import QtWidgets, QtCore, QtGui


class PressHoverButton(QtWidgets.QPushButton):
    """Keep track about mouse press/release and enter/leave."""

    _mouse_pressed = False
    _mouse_hovered = False
    change_state = QtCore.Signal(bool)

    def mousePressEvent(self, event):
        self._mouse_pressed = True
        self._mouse_hovered = True
        self.change_state.emit(self._mouse_hovered)
        super(PressHoverButton, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._mouse_pressed = False
        self._mouse_hovered = False
        self.change_state.emit(self._mouse_hovered)
        super(PressHoverButton, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        mouse_pos = self.mapFromGlobal(QtGui.QCursor.pos())
        under_mouse = self.rect().contains(mouse_pos)
        if under_mouse != self._mouse_hovered:
            self._mouse_hovered = under_mouse
            self.change_state.emit(self._mouse_hovered)

        super(PressHoverButton, self).mouseMoveEvent(event)


class PlaceholderLineEdit(QtWidgets.QLineEdit):
    """Set placeholder color of QLineEdit in Qt 5.12 and higher."""

    def __init__(self, *args, **kwargs):
        super(PlaceholderLineEdit, self).__init__(*args, **kwargs)
        # Change placeholder palette color
        if hasattr(QtGui.QPalette, "PlaceholderText"):
            filter_palette = self.palette()
            color = QtGui.QColor("#D3D8DE")
            color.setAlpha(67)
            filter_palette.setColor(
                QtGui.QPalette.PlaceholderText,
                color
            )
            self.setPalette(filter_palette)
