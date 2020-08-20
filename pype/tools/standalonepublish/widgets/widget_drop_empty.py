from Qt import QtWidgets, QtCore, QtGui


class DropEmpty(QtWidgets.QWidget):

    def __init__(self, parent):
        '''Initialise DataDropZone widget.'''
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)

        BottomCenterAlignment = QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter
        TopCenterAlignment = QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter

        font = QtGui.QFont()
        font.setFamily("DejaVu Sans Condensed")
        font.setPointSize(26)
        font.setBold(True)
        font.setWeight(50)
        font.setKerning(True)

        self._label = QtWidgets.QLabel('Drag & Drop')
        self._label.setFont(font)
        self._label.setStyleSheet(
            'background-color: transparent;'
        )

        font.setPointSize(12)
        self._sub_label = QtWidgets.QLabel('(drop files here)')
        self._sub_label.setFont(font)
        self._sub_label.setStyleSheet(
            'background-color: transparent;'
        )

        layout.addWidget(self._label, alignment=BottomCenterAlignment)
        layout.addWidget(self._sub_label, alignment=TopCenterAlignment)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        pen = QtGui.QPen()
        pen.setWidth(1)
        pen.setBrush(QtCore.Qt.darkGray)
        pen.setStyle(QtCore.Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(
            10,
            10,
            self.rect().width() - 15,
            self.rect().height() - 15
        )
