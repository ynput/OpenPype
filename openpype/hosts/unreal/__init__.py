import os
import openpype.hosts


def add_implementation_envs(env, _app):
    """Modify environments to contain all required for implementation."""
    # Set OPENPYPE_UNREAL_PLUGIN required for Unreal implementation
    unreal_plugin_path = os.path.join(
        os.path.dirname(os.path.abspath(openpype.hosts.__file__)),
        "unreal", "integration"
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
