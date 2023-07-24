import os
from pathlib import Path

from openpype.modules import IHostAddon, OpenPypeModule
from .lib import get_compatible_integration

UNREAL_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class UnrealAddon(OpenPypeModule, IHostAddon):
    name = "unreal"
    host_name = "unreal"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, app):
        """Modify environments to contain all required for implementation."""
        # Set AYON_UNREAL_PLUGIN required for Unreal implementation

        ue_version = app.name.replace("-", ".")
        # NOTE hornet fix for python 2.7
        # unreal_plugin_path = os.path.join(
        #     UNREAL_ROOT_DIR, "integration", f"UE_{ue_version}", "Ayon"
        # )
        unreal_plugin_path = os.path.join(
            UNREAL_ROOT_DIR, "integration", "UE_{}".format(ue_version), "Ayon"
        )
        # END
        if not Path(unreal_plugin_path).exists():
            compatible_versions = get_compatible_integration(
                ue_version, Path(UNREAL_ROOT_DIR) / "integration"
            )
            if compatible_versions:
                unreal_plugin_path = compatible_versions[-1] / "Ayon"
                unreal_plugin_path = unreal_plugin_path.as_posix()

        if not env.get("AYON_UNREAL_PLUGIN") or \
                env.get("AYON_UNREAL_PLUGIN") != unreal_plugin_path:
            env["AYON_UNREAL_PLUGIN"] = unreal_plugin_path

        # Set default environments if are not set via settings
        defaults = {
            "OPENPYPE_LOG_NO_COLORS": "True"
        }
        for key, value in defaults.items():
            if not env.get(key):
                env[key] = value

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(UNREAL_ROOT_DIR, "hooks")
        ]

    def get_workfile_extensions(self):
        return [".uproject"]
