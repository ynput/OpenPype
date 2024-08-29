from openpype import AYON_SERVER_ENABLED
from openpype.modules import OpenPypeModule, ITrayAction


class LogViewModule(OpenPypeModule, ITrayAction):
    name = "log_viewer"
    label = "Show Logs"
    submenu = "More Tools"

    def __init__(self, manager, settings):
        self.window = None

        super().__init__(manager, settings)

    def initialize(self, _modules_settings):
        logging_settings = _modules_settings[self.name]
        self.enabled = logging_settings["enabled"]
        if AYON_SERVER_ENABLED:
            self.enabled = False

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

    def tray_start(self):
        return

    def tray_exit(self):
        # Close window UI
        if self.window:
            self.window.close()

    def on_action_trigger(self):
        if self.window:
            self.window.show()
