from openpype.modules import OpenPypeModule
from openpype_interfaces import ITrayAction


class SettingsAction(OpenPypeModule, ITrayAction):
    """Action to show Setttings tool."""
    name = "settings"
    label = "Studio Settings"
    admin_action = True

    def initialize(self, _modules_settings):
        # This action is always enabled
        self.enabled = True

        # User role
        # TODO should be changeable
        self.user_role = "manager"

        # Tray attributes
        self.settings_window = None

    def tray_init(self):
        """Initialization in tray implementation of ITrayAction."""
        self.create_settings_window()

    def on_action_trigger(self):
        """Implementation for action trigger of ITrayAction."""
        self.show_settings_window()

    def create_settings_window(self):
        """Initializa Settings Qt window."""
        if self.settings_window:
            return
        from openpype.tools.settings import MainWidget

        self.settings_window = MainWidget(self.user_role, reset_on_show=False)
        self.settings_window.trigger_restart.connect(self._on_trigger_restart)

    def _on_trigger_restart(self):
        self.manager.restart_tray()

    def show_settings_window(self):
        """Show settings tool window.

        Raises:
            AssertionError: Window must be already created. Call
                `create_settings_window` before calling this method.
        """
        if not self.settings_window:
            raise AssertionError("Window is not initialized.")

        # Store if was visible
        was_visible = self.settings_window.isVisible()
        was_minimized = self.settings_window.isMinimized()

        # Show settings gui
        self.settings_window.show()

        if was_minimized:
            self.settings_window.showNormal()

        # Pull window to the front.
        self.settings_window.raise_()
        self.settings_window.activateWindow()

        # Reset content if was not visible
        if not was_visible and not was_minimized:
            self.settings_window.reset()


class LocalSettingsAction(OpenPypeModule, ITrayAction):
    """Action to show Setttings tool."""
    name = "local_settings"
    label = "Settings"

    def initialize(self, _modules_settings):
        # This action is always enabled
        self.enabled = True

        # Tray attributes
        self.settings_window = None
        self._first_trigger = True

    def tray_init(self):
        """Initialization in tray implementation of ITrayAction."""
        self.create_settings_window()

    def on_action_trigger(self):
        """Implementation for action trigger of ITrayAction."""
        self.show_settings_window()

    def create_settings_window(self):
        """Initializa Settings Qt window."""
        if self.settings_window:
            return
        from openpype.tools.settings import LocalSettingsWindow
        self.settings_window = LocalSettingsWindow()

    def show_settings_window(self):
        """Show settings tool window.

        Raises:
            AssertionError: Window must be already created. Call
                `create_settings_window` before callint this method.
        """
        if not self.settings_window:
            raise AssertionError("Window is not initialized.")

        # Store if was visible
        was_visible = self.settings_window.isVisible()

        # Show settings gui
        self.settings_window.show()

        # Pull window to the front.
        self.settings_window.raise_()
        self.settings_window.activateWindow()

        # Do not reset if it's first trigger of action
        if self._first_trigger:
            self._first_trigger = False
        elif not was_visible:
            # Reset content if was not visible
            self.settings_window.reset()
