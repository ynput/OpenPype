from openpype.api import Logger
from .. import PypeModule, ITrayModule


class LogViewModule(PypeModule, ITrayModule):
    name = "log_viewer"

    def initialize(self, modules_settings):
        logging_settings = modules_settings[self.name]
        self.enabled = logging_settings["enabled"]

        # Tray attributes
        self.window = None

    def tray_init(self):
        try:
            from .tray.app import LogsWindow
            self.window = LogsWindow()
        except Exception:
            self.log.warning(
                "Couldn't set Logging GUI due to error.", exc_info=True
            )

    # Definition of Tray menu
    def tray_menu(self, tray_menu):
        from Qt import QtWidgets
        # Menu for Tray App
        menu = QtWidgets.QMenu('Logging', tray_menu)

        show_action = QtWidgets.QAction("Show Logs", menu)
        show_action.triggered.connect(self._show_logs_gui)
        menu.addAction(show_action)

        tray_menu.addMenu(menu)

    def tray_start(self):
        return

    def tray_exit(self):
        return

    def connect_with_modules(self, _enabled_modules):
        """Nothing special."""
        return

    def _show_logs_gui(self):
        if self.window:
            self.window.show()
