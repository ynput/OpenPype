import os


def add_implementation_envs(env, _app):
    """Modify environments to contain all required for implementation."""
    # Prepare path to implementation script
    implementation_user_script_path = os.path.join(
        os.environ["OPENPYPE_REPOS_ROOT"],
        "repos",
        "avalon-core",
        "setup",
        "blender"
    )

    # Add blender implementation script path to PYTHONPATH
    python_path = env.get("PYTHONPATH") or ""
    python_path_parts = [
        path
        for path in python_path.split(os.pathsep)
        if path
    ]
    python_path_parts.insert(0, implementation_user_script_path)
    env["PYTHONPATH"] = os.pathsep.join(python_path_parts)

    # Modify Blender user scripts path
    blender_user_scripts = env.get("BLENDER_USER_SCRIPTS") or ""
    previous_user_scripts = []
    for path in blender_user_scripts.split(os.pathsep):
        if path and os.path.exists(path):
            path = os.path.normpath(path)
            if path != implementation_user_script_path:
                previous_user_scripts.append(path)

    env["OPENPYPE_BLENDER_USER_SCRIPTS"] = os.pathsep.join(
        previous_user_scripts
    )
    env["BLENDER_USER_SCRIPTS"] = implementation_user_script_path

    # Define Qt binding if not defined
    if not env.get("QT_PREFERRED_BINDING"):
        env["QT_PREFERRED_BINDING"] = "PySide2"
