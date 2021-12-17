import sys
from Qt import QtWidgets, QtCore, QtGui

from openpype import (
    resources,
    style
)
from openpype.tools.utils import host_tools
from openpype.tools.utils.lib import qt_app_context


class ToolsBtnsWidget(QtWidgets.QWidget):
    """Widget containing buttons which are clickable."""
    tool_required = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(ToolsBtnsWidget, self).__init__(parent)

        create_btn = QtWidgets.QPushButton("Create...", self)
        load_btn = QtWidgets.QPushButton("Load...", self)
        publish_btn = QtWidgets.QPushButton("Publish...", self)
        manage_btn = QtWidgets.QPushButton("Manage...", self)
        experimental_tools_btn = QtWidgets.QPushButton(
            "Experimental tools...", self
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(create_btn, 0)
        layout.addWidget(load_btn, 0)
        layout.addWidget(publish_btn, 0)
        layout.addWidget(manage_btn, 0)
        layout.addWidget(experimental_tools_btn, 0)
        layout.addStretch(1)

        create_btn.clicked.connect(self._on_create)
        load_btn.clicked.connect(self._on_load)
        publish_btn.clicked.connect(self._on_publish)
        manage_btn.clicked.connect(self._on_manage)
        experimental_tools_btn.clicked.connect(self._on_experimental)

    def _on_create(self):
        self.tool_required.emit("creator")

    def _on_load(self):
        self.tool_required.emit("loader")

    def _on_publish(self):
        self.tool_required.emit("publish")

    def _on_manage(self):
        self.tool_required.emit("sceneinventory")

    def _on_experimental(self):
        self.tool_required.emit("experimental_tools")


class ToolsDialog(QtWidgets.QDialog):
    """Dialog with tool buttons that will stay opened until user close it."""
    def __init__(self, *args, **kwargs):
        super(ToolsDialog, self).__init__(*args, **kwargs)

        self.setWindowTitle("OpenPype tools")
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)

        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        tools_widget = ToolsBtnsWidget(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(tools_widget)

        tools_widget.tool_required.connect(self._on_tool_require)
        self._tools_widget = tools_widget

        self._first_show = True

    def sizeHint(self):
        result = super(ToolsDialog, self).sizeHint()
        result.setWidth(result.width() * 2)
        return result

    def showEvent(self, event):
        super(ToolsDialog, self).showEvent(event)
        if self._first_show:
            self.setStyleSheet(style.load_stylesheet())
            self._first_show = False

    def _on_tool_require(self, tool_name):
        host_tools.show_tool_by_name(tool_name, parent=self)


class ToolsPopup(ToolsDialog):
    """Popup with tool buttons that will close when loose focus."""
    def __init__(self, *args, **kwargs):
        super(ToolsPopup, self).__init__(*args, **kwargs)

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.Popup
        )

    def showEvent(self, event):
        super(ToolsPopup, self).showEvent(event)
        app = QtWidgets.QApplication.instance()
        app.processEvents()
        pos = QtGui.QCursor.pos()
        self.move(pos)


class WindowCache:
    """Cached objects and methods to be used in global scope."""
    _dialog = None
    _popup = None
    _first_show = True

    @classmethod
    def _before_show(cls):
        """Create QApplication if does not exists yet."""
        if not cls._first_show:
            return

        cls._first_show = False
        if not QtWidgets.QApplication.instance():
            QtWidgets.QApplication(sys.argv)

    @classmethod
    def show_popup(cls):
        cls._before_show()
        with qt_app_context():
            if cls._popup is None:
                cls._popup = ToolsPopup()

            cls._popup.show()

    @classmethod
    def show_dialog(cls):
        cls._before_show()
        with qt_app_context():
            if cls._dialog is None:
                cls._dialog = ToolsDialog()

            cls._dialog.show()
            cls._dialog.raise_()
            cls._dialog.activateWindow()


def show_tools_popup():
    WindowCache.show_popup()


def show_tools_dialog():
    WindowCache.show_dialog()
