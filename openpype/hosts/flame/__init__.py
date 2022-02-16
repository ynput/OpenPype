import os

HOST_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


def add_implementation_envs(env, _app):
    # Add requirements to DL_PYTHON_HOOK_PATH
    pype_root = os.environ["OPENPYPE_REPOS_ROOT"]
    new_flame_paths = os.path.join(
        pype_root, "openpype", "hosts", "flame", "startup")

    env["DL_PYTHON_HOOK_PATH"] = os.pathsep.join(new_flame_paths)
    env.pop("QT_AUTO_SCREEN_SCALE_FACTOR", None)

    # Set default values if are not already set via settings
    defaults = {
        "LOGLEVEL": "DEBUG"
    }
    for key, value in defaults.items():
        if not env.get(key):
            env[key] = value
