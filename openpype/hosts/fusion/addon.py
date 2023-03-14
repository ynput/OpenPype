import os
import re
from openpype.modules import OpenPypeModule, IHostAddon
from openpype.lib import Logger

FUSION_HOST_DIR = os.path.dirname(os.path.abspath(__file__))


def get_fusion_profile_number(module: str, app_data: str) -> int:
    """
    FUSION_PROFILE_VERSION variable is used by the pre-launch hooks.
    Since Fusion v16, the profile folder variable became version-specific,
    but then it was abandoned by BlackmagicDesign devs, and now, despite it is
    already Fusion version 18, still FUSION16_PROFILE_DIR is used.
    The variable is added in case the version number will be
    updated or deleted so we could easily change the version or disable it.

    app_data derives from `launch_context.env.get("AVALON_APP_NAME")`. 
    For the time being we will encourage user to set a version number 
    set in the system settings key for the Blackmagic Fusion.
    """

    log = Logger.get_logger(__name__)

    if not app_data:
        return
    fusion16_profile_versions = ("16", "17", "18")
    try:
        app_version = re.search(r"fusion/(\d+)", app_data).group(1)
        log.info(f"{module} found Fusion profile version: {app_version}")
        if app_version in fusion16_profile_versions:
            return 16
        elif app_version == "9":
            return 9
    except AttributeError:
        log.info("Fusion version was not found in the app data")


class FusionAddon(OpenPypeModule, IHostAddon):
    name = "fusion"
    host_name = "fusion"

    def initialize(self, module_settings):
        self.enabled = True

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [os.path.join(FUSION_HOST_DIR, "hooks")]

    def add_implementation_envs(self, env, _app):
        # Set default values if are not already set via settings
        defaults = {"OPENPYPE_LOG_NO_COLORS": "Yes"}
        for key, value in defaults.items():
            if not env.get(key):
                env[key] = value

    def get_workfile_extensions(self):
        return [".comp"]
