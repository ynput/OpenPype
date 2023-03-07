import os
from openpype.modules import OpenPypeModule, IHostAddon

FUSION_HOST_DIR = os.path.dirname(os.path.abspath(__file__))

FUSION_PROFILE_VERSION = 16

# FUSION_PROFILE_VERSION variable is used by the pre-launch hooks.
# Since Fusion v16, the profile folder became project-specific,
# but then it was abandoned by BlackmagicDesign devs, and now, despite it is
# already Fusion version 18, still FUSION16_PROFILE_DIR is used.
# The variable is added in case the version number will be
# updated or deleted so we could easily change the version or disable it.


class FusionAddon(OpenPypeModule, IHostAddon):
    name = "fusion"
    host_name = "fusion"

    def initialize(self, module_settings):
        self.enabled = True

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(FUSION_HOST_DIR, "hooks")
        ]

    def add_implementation_envs(self, env, _app):
        # Set default values if are not already set via settings
        defaults = {
            "OPENPYPE_LOG_NO_COLORS": "Yes"
        }
        for key, value in defaults.items():
            if not env.get(key):
                env[key] = value

    def get_workfile_extensions(self):
        return [".comp"]
