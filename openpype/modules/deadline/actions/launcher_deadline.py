import subprocess
import os
import platform
import acre
from openpype.pipeline import LauncherAction
from openpype.modules import ModulesManager
from openpype.client import get_project, get_asset_by_name
from openpype.lib.applications import parse_environments, _merge_env
from openpype.settings import (
    get_system_settings,
    get_general_environments
)

class LaunchDeadline(LauncherAction):
    name = "launchdeadline"
    label = "Launch Deadline"
    icon = "/prod/softprod/apps/deadline/10.1.23.6/linux/icons/Deadline_Monitor.png"
    color = "#e0e1e1"
    order = 10

    @staticmethod
    def get_deadline_module():
        return ModulesManager().modules_by_name.get("deadline")

    def is_compatible(self, session):
        if not session.get("AVALON_PROJECT"):
            return False

        return True

    def process(self, session, **kwargs):
        print("Launching Deadline")
        # # Get deadline settings
        # deadline_settings = get_system_settings()["modules"]["deadline"]
        # env_variables = deadline_settings[0]["environment"]
        # deadline_paths = deadline_settings[0]["deadline_paths"]
        # deadline_urls = deadline_settings[0]["deadline_urls"]
        # print(deadline_urls)

        # merge_envs = acre.merge(env_variables, os.environ)
        # parsed_env_variables = acre.compute(merge_envs, cleanup=False)

        # for key, value in parsed_env_variables.items():
        #     os.environ[key] = value

        # # Call the method to open the app
        # process = subprocess.Popen(["xterm", "-e", deadline_paths["linux"][0]])
