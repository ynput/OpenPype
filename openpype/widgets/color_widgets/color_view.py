from qtpy import QtWidgets, QtCore, QtGui


def draw_checkerboard_tile(piece_size=None, color_1=None, color_2=None):
    if piece_size is None:
        piece_size = 7

    # Make sure piece size is not float
    piece_size = int(piece_size)
    if color_1 is None:
        color_1 = QtGui.QColor(188, 188, 188)

    if color_2 is None:
        color_2 = QtGui.QColor(90, 90, 90)

    pix = QtGui.QPixmap(piece_size * 2, piece_size * 2)
    pix_painter = QtGui.QPainter(pix)

    rect = QtCore.QRect(
        0, 0, piece_size, piece_size
    )
    pix_painter.fillRect(rect, color_1)
    rect.moveTo(piece_size, piece_size)
    pix_painter.fillRect(rect, color_1)
    rect.moveTo(piece_size, 0)
    pix_painter.fillRect(rect, color_2)
    rect.moveTo(0, piece_size)
    pix_painter.fillRect(rect, color_2)
    pix_painter.end()

    return pix


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
            self._checkerboard = draw_checkerboard_tile(4)
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
        clip_rect = event.rect()
        rect = clip_rect.adjusted(0, 0, -1, -1)

        painter = QtGui.QPainter(self)
        painter.setClipRect(clip_rect)
        painter.drawTiledPixmap(rect, self.checkerboard())
        painter.setBrush(self.actual_color)
        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 67))
        painter.setPen(pen)
        painter.drawRect(rect)
        painter.end()
