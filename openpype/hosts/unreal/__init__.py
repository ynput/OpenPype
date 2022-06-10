import os
import openpype.hosts
from openpype.lib.applications import Application


def add_implementation_envs(env: dict, _app: Application) -> None:
    """Modify environments to contain all required for implementation."""
    # Set OPENPYPE_UNREAL_PLUGIN required for Unreal implementation

    ue_plugin = "UE_5.0" if _app.name[:1] == "5" else "UE_4.7"
    unreal_plugin_path = os.path.join(
        os.path.dirname(os.path.abspath(openpype.hosts.__file__)),
        "unreal", "integration", ue_plugin
    )
    if not env.get("OPENPYPE_UNREAL_PLUGIN"):
        env["OPENPYPE_UNREAL_PLUGIN"] = unreal_plugin_path

    # Set default environments if are not set via settings
    defaults = {
        "OPENPYPE_LOG_NO_COLORS": "True"
    }
    for key, value in defaults.items():
        if not env.get(key):
            env[key] = value
