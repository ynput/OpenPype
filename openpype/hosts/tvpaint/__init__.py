import os


def add_implementation_envs(env, _app):
    """Modify environments to contain all required for implementation."""
    defaults = {
        "OPENPYPE_LOG_NO_COLORS": "True"
    }
    for key, value in defaults.items():
        if not env.get(key):
            env[key] = value


def get_launch_script_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(
        current_dir,
        "api",
        "launch_script.py"
    )
