from . import PypeModule, ITrayModule


class SettingsModule(PypeModule, ITrayModule):
    name = "settings"

    def initialize(self, _modules_settings):
        # This module is always enabled
        self.enabled = True

        # User role
        # TODO should be changeable
        self.user_role = "developer"

        # Tray attributes
        self.settings_window = None

    def connect_with_modules(self, *_a, **_kw):
        return

    def create_settings_window(self):
        if self.settings_window:
            return
        from pype.tools.settings import MainWidget
        self.settings_window = MainWidget(self.user_role)

    def show_settings_window(self):
        if not self.settings_window:
            raise AssertionError("Window is not initialized.")

        self.settings_window.show()

        # Pull window to the front.
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def tray_init(self):
        self.create_settings_window()

    def tray_menu(self, tray_menu):
        """Add **change credentials** option to tray menu."""
        from Qt import QtWidgets

        # Actions
        action = QtWidgets.QAction("Settings", tray_menu)
        action.triggered.connect(self.show_settings_window)
        tray_menu.addAction(action)

    def tray_start(self):
        return

    def tray_exit(self):
        return
