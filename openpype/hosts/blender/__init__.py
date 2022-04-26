import os


def add_implementation_envs(env, _app):
    """Modify environments to contain all required for implementation."""
    # Prepare path to implementation script
    implementation_user_script_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "blender_addon"
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
    previous_user_scripts = set()
    # Implementation path is added to set for easier paths check inside loops
    # - will be removed at the end
    previous_user_scripts.add(implementation_user_script_path)

    openpype_blender_user_scripts = (
        env.get("OPENPYPE_BLENDER_USER_SCRIPTS") or ""
    )
    for path in openpype_blender_user_scripts.split(os.pathsep):
        if path:
            previous_user_scripts.add(os.path.normpath(path))

    blender_user_scripts = env.get("BLENDER_USER_SCRIPTS") or ""
    for path in blender_user_scripts.split(os.pathsep):
        if path:
            previous_user_scripts.add(os.path.normpath(path))

    # Remove implementation path from user script paths as is set to
    #   `BLENDER_USER_SCRIPTS`
    previous_user_scripts.remove(implementation_user_script_path)
    env["BLENDER_USER_SCRIPTS"] = implementation_user_script_path

    # Set custom user scripts env
    env["OPENPYPE_BLENDER_USER_SCRIPTS"] = os.pathsep.join(
        previous_user_scripts
    )

    # Define Qt binding if not defined
    if not env.get("QT_PREFERRED_BINDING"):
        env["QT_PREFERRED_BINDING"] = "PySide2"
