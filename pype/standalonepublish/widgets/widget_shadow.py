from . import QtWidgets, QtCore, QtGui


class ShadowWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        self.parent_widget = parent
        super().__init__(parent)
        w = self.parent_widget.frameGeometry().width()
        h = self.parent_widget.frameGeometry().height()
        self.resize(QtCore.QSize(w, h))
        palette = QtGui.QPalette(self.palette())
        palette.setColor(palette.Background, QtCore.Qt.transparent)
        self.setPalette(palette)
        self.message = ''

        font = QtGui.QFont()
        font.setFamily("DejaVu Sans Condensed")
        font.setPointSize(40)
        font.setBold(True)
        font.setWeight(50)
        font.setKerning(True)
        self.font = font

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setFont(self.font)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(event.rect(), QtGui.QBrush(QtGui.QColor(0, 0, 0, 127)))
        painter.drawText(
            QtCore.QRectF(
                0.0,
                0.0,
                self.parent_widget.frameGeometry().width(),
                self.parent_widget.frameGeometry().height()
            ),
            QtCore.Qt.AlignCenter|QtCore.Qt.AlignCenter,
            self.message
        )
        painter.end()
