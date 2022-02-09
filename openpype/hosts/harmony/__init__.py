import os


def add_implementation_envs(env, _app):
    """Modify environments to contain all required for implementation."""
    openharmony_path = os.path.join(
        os.environ["OPENPYPE_REPOS_ROOT"], "openpype", "hosts",
        "harmony", "vendor", "OpenHarmony"
    )
    # TODO check if is already set? What to do if is already set?
    env["LIB_OPENHARMONY_PATH"] = openharmony_path
