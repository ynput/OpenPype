from Qt import QtWidgets, QtCore, QtGui


class ColorViewer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ColorViewer, self).__init__(parent)

        self.setMinimumSize(10, 10)

        self.alpha = 255
        self.actual_pen = QtGui.QPen()
        self.actual_color = QtGui.QColor()
        self._checkerboard = None

    def checkerboard(self):
        if not self._checkerboard:
            checkboard_piece_size = 10
            color_1 = QtGui.QColor(188, 188, 188)
            color_2 = QtGui.QColor(90, 90, 90)

            pix = QtGui.QPixmap(
                checkboard_piece_size * 2,
                checkboard_piece_size * 2
            )
            pix_painter = QtGui.QPainter(pix)

            rect = QtCore.QRect(
                0, 0, checkboard_piece_size, checkboard_piece_size
            )
            pix_painter.fillRect(rect, color_1)
            rect.moveTo(checkboard_piece_size, checkboard_piece_size)
            pix_painter.fillRect(rect, color_1)
            rect.moveTo(checkboard_piece_size, 0)
            pix_painter.fillRect(rect, color_2)
            rect.moveTo(0, checkboard_piece_size)
            pix_painter.fillRect(rect, color_2)
            pix_painter.end()
            self._checkerboard = pix

        return self._checkerboard

    def color(self):
        return self.actual_color

    def set_color(self, color):
        if color == self.actual_color:
            return

        # Create copy of entered color
        self.actual_color = QtGui.QColor(color)
        # Set alpha by current alpha value
        self.actual_color.setAlpha(self.alpha)
        # Repaint
        self.update()

    def set_alpha(self, alpha):
        if alpha == self.alpha:
            return
        # Change alpha of current color
        self.actual_color.setAlpha(alpha)
        # Store the value
        self.alpha = alpha
        # Repaint
        self.update()

    def paintEvent(self, event):
        rect = event.rect()

        # Paint everything to pixmap as it has transparency
        pix = QtGui.QPixmap(rect.width(), rect.height())
        pix_painter = QtGui.QPainter(pix)
        pix_painter.drawTiledPixmap(rect, self.checkerboard())
        pix_painter.fillRect(rect, self.actual_color)
        pix_painter.end()

        painter = QtGui.QPainter(self)
        painter.drawPixmap(rect, pix)
        painter.end()
