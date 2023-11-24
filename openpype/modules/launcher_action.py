import os

from openpype import PLUGINS_DIR, AYON_SERVER_ENABLED
from openpype.modules import (
    OpenPypeModule,
    ITrayAction,
)


class LauncherAction(OpenPypeModule, ITrayAction):
    label = "Launcher"
    name = "launcher_tool"

    def initialize(self, _modules_settings):
        # This module is always enabled
        self.enabled = True

        # Tray attributes
        self._window = None

    def tray_init(self):
        self._create_window()

        self.add_doubleclick_callback(self._show_launcher)

    def tray_start(self):
        return

    def connect_with_modules(self, enabled_modules):
        # Register actions
        if not self.tray_initialized:
            return

        from openpype.pipeline.actions import register_launcher_action_path

        actions_dir = os.path.join(PLUGINS_DIR, "actions")
        if os.path.exists(actions_dir):
            register_launcher_action_path(actions_dir)

        actions_paths = self.manager.collect_plugin_paths()["actions"]
        for path in actions_paths:
            if path and os.path.exists(path):
                register_launcher_action_path(path)

        paths_str = os.environ.get("AVALON_ACTIONS") or ""
        if paths_str:
            self.log.warning(
                "WARNING: 'AVALON_ACTIONS' is deprecated. Support of this"
                " environment variable will be removed in future versions."
                " Please consider using 'OpenPypeModule' to define custom"
                " action paths. Planned version to drop the support"
                " is 3.17.2 or 3.18.0 ."
            )

        for path in paths_str.split(os.pathsep):
            if path and os.path.exists(path):
                register_launcher_action_path(path)

    def on_action_trigger(self):
        """Implementation for ITrayAction interface.

        Show launcher tool on action trigger.
        """

        self._show_launcher()

    def _create_window(self):
        if self._window:
            return
        if AYON_SERVER_ENABLED:
            from openpype.tools.ayon_launcher.ui import LauncherWindow
        else:
            from openpype.tools.launcher import LauncherWindow
        self._window = LauncherWindow()

    def _show_launcher(self):
        if self._window is None:
            return
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
