from openpype.modules import OpenPypeModule
from openpype_interfaces import ITrayAction


class LauncherAction(OpenPypeModule, ITrayAction):
    label = "Launcher"
    name = "launcher_tool"

    def initialize(self, _modules_settings):
        # This module is always enabled
        self.enabled = True

        # Tray attributes
        self.window = None

    def tray_init(self):
        self.create_window()

        self.add_doubleclick_callback(self.show_launcher)

    def tray_start(self):
        return

    def connect_with_modules(self, enabled_modules):
        # Register actions
        if self.tray_initialized:
            from openpype.tools.launcher import actions
            actions.register_config_actions()
            actions_paths = self.manager.collect_plugin_paths()["actions"]
            actions.register_actions_from_paths(actions_paths)
            actions.register_environment_actions()

    def create_window(self):
        if self.window:
            return
        from openpype.tools.launcher import LauncherWindow
        self.window = LauncherWindow()

    def on_action_trigger(self):
        self.show_launcher()

    def show_launcher(self):
        if self.window:
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()
