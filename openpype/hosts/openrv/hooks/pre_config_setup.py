import os
import platform

from openpype.lib import PreLaunchHook
from openpype.settings import (
    get_project_settings
)


SET_CONFIG_FILE_PATH = None
SET_OCIO_ENV_VAR = None
SET_USERS_CONFIG = None
SET_AOV_CONFIGS = None
SET_STARTUP_PROJECT = None


class PreConfigSetups(PreLaunchHook):
    app_groups = ["openrv"]

    def execute(self):
        self.log.info("PRE-SETUP OPENRV CONFIGS HOOK")

        self.project_name = self.launch_context.env.get("AVALON_PROJECT")
        if not self.project_name:
            self.project_name = os.environ.get("AVALON_PROJECT")

        print("Loaded project", self.project_name)

        self.load_config = get_project_settings(self.project_name)["openrv"]["imageio"]["workfile"]["OCIO_config"]
        print(self.load_config)

        if "srgb" in self.load_config.lower():
            print("OCIO Disabled.")
            os.environ["OCIO"] = ""
            self.launch_context.env["OCIO"] = ""
        else:
            print("OCIO Enabled.")
            ocio_config_path = get_project_settings(self.project_name)["openrv"]["imageio"]["workfile"]["customOCIOConfigPath"][str(platform.system().lower())][0]
            os.environ["OCIO"] = str(ocio_config_path)
            self.launch_context.env["OCIO"] = str(ocio_config_path)
            print(os.environ["OCIO"])
