from Qt import QtWidgets, QtCore


class FilesView(QtWidgets.QTreeView):
    doubleClickedLeft = QtCore.Signal()
    doubleClickedRight = QtCore.Signal()

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.doubleClickedLeft.emit()

        elif event.button() == QtCore.Qt.RightButton:
            self.doubleClickedRight.emit()

        return super(FilesView, self).mouseDoubleClickEvent(event)
