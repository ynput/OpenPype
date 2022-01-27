import sys
import logging
from Qt import QtWidgets, QtCore

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
    """
        Produces centered dialog with specific level denoting severity
    Args:
        title: (string) dialog title
        message: (string) message
        level: (string) info|warning|critical
        parent: (QtWidgets.QApplication)

    Returns:
         None
    """
    app = parent
    if not app:
        app = QtWidgets.QApplication(sys.argv)

    ex = Window(app, title, message, level)
    ex.show()

    # Move widget to center of screen
    try:
        desktop_rect = QtWidgets.QApplication.desktop().availableGeometry(ex)
        center = desktop_rect.center()
        ex.move(
            center.x() - (ex.width() * 0.5),
            center.y() - (ex.height() * 0.5)
        )
    except Exception:
        # skip all possible issues that may happen feature is not crutial
        log.warning("Couldn't center message.", exc_info=True)
    # sys.exit(app.exec_())


class ScrollMessageBox(QtWidgets.QDialog):
    """
        Basic version of scrollable QMessageBox. No other existing dialog
        implementation is scrollable.
        Args:
            icon: <QtWidgets.QMessageBox.Icon>
            title: <string>
            messages: <list> of messages
            cancelable: <boolean> - True if Cancel button should be added
    """
    def __init__(self, icon, title, messages, cancelable=False):
        super(ScrollMessageBox, self).__init__()
        self.setWindowTitle(title)
        self.icon = icon

        self.setWindowFlags(QtCore.Qt.WindowTitleHint)

        layout = QtWidgets.QVBoxLayout(self)

        scroll_widget = QtWidgets.QScrollArea(self)
        scroll_widget.setWidgetResizable(True)
        content_widget = QtWidgets.QWidget(self)
        scroll_widget.setWidget(content_widget)

        max_len = 0
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        for message in messages:
            label_widget = QtWidgets.QLabel(message, content_widget)
            content_layout.addWidget(label_widget)
            max_len = max(max_len, len(message))

        # guess size of scrollable area
        max_width = QtWidgets.QApplication.desktop().availableGeometry().width
        scroll_widget.setMinimumWidth(min(max_width, max_len * 6))
        layout.addWidget(scroll_widget)

        if not cancelable:  # if no specific buttons OK only
            buttons = QtWidgets.QDialogButtonBox.Ok
        else:
            buttons = QtWidgets.QDialogButtonBox.Ok | \
                      QtWidgets.QDialogButtonBox.Cancel

        btn_box = QtWidgets.QDialogButtonBox(buttons)
        btn_box.accepted.connect(self.accept)

        if cancelable:
            btn_box.reject.connect(self.reject)

        btn = QtWidgets.QPushButton('Copy to clipboard')
        btn.clicked.connect(lambda: QtWidgets.QApplication.
                            clipboard().setText("\n".join(messages)))
        btn_box.addButton(btn, QtWidgets.QDialogButtonBox.NoRole)

        layout.addWidget(btn_box)
        self.show()
