from xml.dom import minidom

from . import QtGui, QtCore, QtWidgets
from PyQt5 import QtSvg, QtXml


class SvgResizable(QtSvg.QSvgWidget):
    clicked = QtCore.Signal()

    def __init__(self, filepath, width=None, height=None, fill=None):
        super().__init__()
        self.xmldoc = minidom.parse(filepath)
        itemlist = self.xmldoc.getElementsByTagName('svg')
        for element in itemlist:
            if fill:
                element.setAttribute('fill', str(fill))
        # TODO auto scale if only one is set
        if width is not None and height is not None:
            self.setMaximumSize(width, height)
            self.setMinimumSize(width, height)
        xml_string = self.xmldoc.toxml()
        svg_bytes = bytearray(xml_string, encoding='utf-8')

        self.load(svg_bytes)

    def change_color(self, color):
        element = self.xmldoc.getElementsByTagName('svg')[0]
        element.setAttribute('fill', str(color))
        xml_string = self.xmldoc.toxml()
        svg_bytes = bytearray(xml_string, encoding='utf-8')
        self.load(svg_bytes)

    def mousePressEvent(self, event):
        self.clicked.emit()


class SvgButton(QtWidgets.QFrame):
    clicked = QtCore.Signal()
    def __init__(
        self, filepath, width=None, height=None, fills=[],
        parent=None, checkable=True
    ):
        super().__init__(parent)
        self.checkable = checkable
        self.checked = False

        xmldoc = minidom.parse(filepath)
        element = xmldoc.getElementsByTagName('svg')[0]
        c_actual = '#777777'
        if element.hasAttribute('fill'):
            c_actual = element.getAttribute('fill')
        self.store_fills(fills, c_actual)

        self.installEventFilter(self)
        self.svg_widget = SvgResizable(filepath, width, height, self.c_normal)
        xmldoc = minidom.parse(filepath)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.svg_widget)

        if width is not None and height is not None:
            self.setMaximumSize(width, height)
            self.setMinimumSize(width, height)

    def store_fills(self, fills, actual):
        if len(fills) == 0:
            fills = [actual, actual, actual, actual]
        elif len(fills) == 1:
            fills = [fills[0], fills[0], fills[0], fills[0]]
        elif len(fills) == 2:
            fills = [fills[0], fills[1], fills[1], fills[1]]
        elif len(fills) == 3:
            fills = [fills[0], fills[1], fills[2], fills[2]]
        self.c_normal = fills[0]
        self.c_hover = fills[1]
        self.c_active = fills[2]
        self.c_active_hover = fills[3]

    def eventFilter(self, object, event):
            if event.type() == QtCore.QEvent.Enter:
                self.hoverEnterEvent(event)
                return True
            elif event.type() == QtCore.QEvent.Leave:
                self.hoverLeaveEvent(event)
                return True
            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                self.mousePressEvent(event)
            return False

    def change_checked(self, hover=True):
        if self.checkable:
            self.checked = not self.checked
        if hover:
            self.hoverEnterEvent()
        else:
            self.hoverLeaveEvent()

    def hoverEnterEvent(self, event=None):
        color = self.c_hover
        if self.checked:
            color = self.c_active_hover
        self.svg_widget.change_color(color)

    def hoverLeaveEvent(self, event=None):
        color = self.c_normal
        if self.checked:
            color = self.c_active
        self.svg_widget.change_color(color)

    def mousePressEvent(self, event=None):
        self.clicked.emit()
