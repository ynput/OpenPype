import os

from openpype.modules import (
    OpenPypeModule,
    ITrayModule,
    IPluginPaths,
)

SHOTGRID_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class ShotgridModule(OpenPypeModule, ITrayModule, IPluginPaths):
    leecher_manager_url = None
    name = "shotgrid"
    enabled = False
    project_id = None
    tray_wrapper = None

    def initialize(self, modules_settings):
        shotgrid_settings = modules_settings.get(self.name, dict())
        self.enabled = shotgrid_settings.get("enabled", False)
        self.leecher_manager_url = shotgrid_settings.get(
            "leecher_manager_url", ""
        )

    def connect_with_modules(self, enabled_modules):
        pass

    def get_global_environments(self):
        return {"PROJECT_ID": self.project_id}

    def get_plugin_paths(self):
        return {
            "publish": [
                os.path.join(SHOTGRID_MODULE_DIR, "plugins", "publish")
            ]
        }

    def get_launch_hook_paths(self):
        return os.path.join(SHOTGRID_MODULE_DIR, "hooks")

    ### Starts Alkemy-X Override ###
    # Remove Shotgrid Login Dialog as it's useless for us, we can use $USER directly

    def tray_init(self):
        pass

    def tray_start(self):
        pass

    def tray_exit(self, *args, **kwargs):
        pass

    def tray_menu(self, tray_menu):
        pass
    ### Ends Alkemy-X Override ###
