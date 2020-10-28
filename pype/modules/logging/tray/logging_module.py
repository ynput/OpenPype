from pype.api import Logger


class LoggingModule:
    def __init__(self, main_parent=None, parent=None):
        self.parent = parent
        self.log = Logger().get_logger(self.__class__.__name__, "logging")

        self.window = None

        self.tray_init(main_parent, parent)

    def tray_init(self, main_parent, parent):
        try:
            from .gui.app import LogsWindow
            self.window = LogsWindow()
            self.tray_menu = self._tray_menu
        except Exception:
            self.log.warning(
                "Couldn't set Logging GUI due to error.", exc_info=True
            )

    # Definition of Tray menu
    def _tray_menu(self, parent_menu):
        from Qt import QtWidgets
        # Menu for Tray App
        menu = QtWidgets.QMenu('Logging', parent_menu)

        show_action = QtWidgets.QAction("Show Logs", menu)
        show_action.triggered.connect(self._show_logs_gui)
        menu.addAction(show_action)

        parent_menu.addMenu(menu)

    def tray_start(self):
        pass

    def process_modules(self, modules):
        return

    def _show_logs_gui(self):
        if self.window:
            self.window.show()
