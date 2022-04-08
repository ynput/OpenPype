import os
import threading

from openpype_interfaces import (
    ITrayModule,
    IPluginPaths,
    ILaunchHookPaths,
)

from openpype.modules import OpenPypeModule

SHOTGRID_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class ShotgridModule(
    OpenPypeModule, ITrayModule, IPluginPaths, ILaunchHookPaths
):
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

    def tray_init(self):
        from .tray.shotgrid_tray import ShotgridTrayWrapper
        from .aop.patch import patch_avalon_db

        patch_avalon_db()
        threading.Timer(10.0, patch_avalon_db).start()

        self.tray_wrapper = ShotgridTrayWrapper(self)


    def tray_start(self):
        return self.tray_wrapper.validate()

    def tray_exit(self, *args, **kwargs):
        return self.tray_wrapper

    def tray_menu(self, tray_menu):
        return self.tray_wrapper.tray_menu(tray_menu)
