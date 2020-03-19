from Qt import QtWidgets
import sys
import logging

log = logging.getLogger(__name__)


class Window(QtWidgets.QWidget):
    def __init__(self, parent, title, message, level):
        super(Window, self).__init__()
        self.parent = parent
        self.title = title
        self.message = message
        self.level = level

        if self.level == "info":
            self._info()
        elif self.level == "warning":
            self._warning()
        elif self.level == "critical":
            self._critical()

    def _info(self):
        self.setWindowTitle(self.title)
        rc = QtWidgets.QMessageBox.information(
            self, self.title, self.message)
        if rc:
            self.exit()

    def _warning(self):
        self.setWindowTitle(self.title)
        rc = QtWidgets.QMessageBox.warning(
            self, self.title, self.message)
        if rc:
            self.exit()

    def _critical(self):
        self.setWindowTitle(self.title)
        rc = QtWidgets.QMessageBox.critical(
            self, self.title, self.message)
        if rc:
            self.exit()

    def exit(self):
        self.hide()
        # self.parent.exec_()
        # self.parent.hide()
        return


def message(title=None, message=None, level="info", parent=None):
    app = parent
    if not app:
        app = QtWidgets.QApplication(sys.argv)
    ex = Window(app, title, message, level)
    ex.show()
    # sys.exit(app.exec_())
