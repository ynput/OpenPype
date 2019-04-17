import os
import logging
import clique
from . import QtWidgets, QtCore, QtGui


class DropDataWidget(QtWidgets.QWidget):

    def __init__(self, parent):
        '''Initialise DataDropZone widget.'''
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)

        CenterAlignment = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter

        self._label = QtWidgets.QLabel('Drop files here')
        layout.addWidget(
            self._label,
            alignment=CenterAlignment
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        pen = QtGui.QPen()
        pen.setWidth(1);
        pen.setBrush(QtCore.Qt.darkGray);
        pen.setStyle(QtCore.Qt.DashLine);
        painter.setPen(pen)
        painter.drawRect(
            10, 10,
            self.rect().width()-15, self.rect().height()-15
        )
