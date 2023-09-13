import os
import re
from openpype.modules import OpenPypeModule, IHostAddon
from openpype.lib import Logger

FUSION_HOST_DIR = os.path.dirname(os.path.abspath(__file__))

# FUSION_VERSIONS_DICT is used by the pre-launch hooks
# The keys correspond to all currently supported Fusion versions
# Each value is a list of corresponding Python home variables and a profile
# number, which is used by the profile hook to set Fusion profile variables.
FUSION_VERSIONS_DICT = {
    9: ("FUSION_PYTHON36_HOME", 9),
    16: ("FUSION16_PYTHON36_HOME", 16),
    17: ("FUSION16_PYTHON36_HOME", 16),
    18: ("FUSION_PYTHON3_HOME", 16),
}


def get_fusion_version(app_name):
    """
    The function is triggered by the prelaunch hooks to get the fusion version.

    `app_name` is obtained by prelaunch hooks from the
    `launch_context.env.get("AVALON_APP_NAME")`.

    To get a correct Fusion version, a version number should be present
    in the `applications/fusion/variants` key
    of the Blackmagic Fusion Application Settings.
    """

    log = Logger.get_logger(__name__)

    if not app_name:
        return

    app_version_candidates = re.findall(r"\d+", app_name)
    if not app_version_candidates:
        return
    for app_version in app_version_candidates:
        if int(app_version) in FUSION_VERSIONS_DICT:
            return int(app_version)
        else:
            log.info(
                "Unsupported Fusion version: {app_version}".format(
                    app_version=app_version
                )
            )


class FusionAddon(OpenPypeModule, IHostAddon):
    name = "fusion"
    host_name = "fusion"

    def initialize(self, module_settings):
        self.enabled = True

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [os.path.join(FUSION_HOST_DIR, "hooks")]

    def add_implementation_envs(self, env, app):
        # Set default values if are not already set via settings
        app_version = app.name
        if int(app_version) < 18:
            python_path = env["PYTHONPATH"]
            python_path_parts = []
            if python_path:
                python_path_parts = python_path.split(os.pathsep)
            vendor_path = os.path.join(FUSION_HOST_DIR, "vendor")
            python_path_parts.insert(0, vendor_path)
            env["PYTHONPATH"] = os.pathsep.join(python_path_parts)

        defaults = {"OPENPYPE_LOG_NO_COLORS": "Yes"}
        for key, value in defaults.items():
            if not env.get(key):
                env[key] = value

    def get_workfile_extensions(self):
        return [".comp"]
