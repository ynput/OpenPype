from Qt import QtWidgets
from pype.api import Logger
from ..gui.app import LogsWindow


class LoggingModule:
    def __init__(self, main_parent=None, parent=None):
        self.parent = parent
        self.log = Logger().get_logger(self.__class__.__name__, "logging")

        try:
            self.window = LogsWindow()
            self.tray_menu = self._tray_menu
        except Exception:
            self.log.warning(
                "Couldn't set Logging GUI due to error.", exc_info=True
            )

    # Definition of Tray menu
    def _tray_menu(self, parent_menu):
        # Menu for Tray App
        menu = QtWidgets.QMenu('Logging', parent_menu)
        # menu.setProperty('submenu', 'on')

        show_action = QtWidgets.QAction("Show Logs", menu)
        show_action.triggered.connect(self.on_show_logs)
        menu.addAction(show_action)

        parent_menu.addMenu(menu)

    def tray_start(self):
        pass

    def process_modules(self, modules):
        return

    def on_show_logs(self):
        self.window.show()
