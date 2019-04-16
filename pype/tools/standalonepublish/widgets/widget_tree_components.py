from . import QtCore, QtGui, QtWidgets


class TreeComponents(QtWidgets.QTreeWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.invisibleRootItem().setFlags(QtCore.Qt.ItemIsEnabled)
        self.setIndentation(28)
        self.headerItem().setText(0, 'Components')

        self.setRootIsDecorated(False)

        self.itemDoubleClicked.connect(lambda i, c: i.double_clicked(c))
