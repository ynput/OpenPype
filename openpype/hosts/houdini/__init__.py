import os


def add_implementation_envs(env, _app):
    # Add requirements to HOUDINI_PATH and HOUDINI_MENU_PATH
    pype_root = os.environ["OPENPYPE_REPOS_ROOT"]

    startup_path = os.path.join(
        pype_root, "openpype", "hosts", "houdini", "startup"
    )
    new_houdini_path = [startup_path]
    new_houdini_menu_path = [startup_path]

    old_houdini_path = env.get("HOUDINI_PATH") or ""
    old_houdini_menu_path = env.get("HOUDINI_MENU_PATH") or ""

    for path in old_houdini_path.split(os.pathsep):
        if not path:
            continue

        norm_path = os.path.normpath(path)
        if norm_path not in new_houdini_path:
            new_houdini_path.append(norm_path)

    for path in old_houdini_menu_path.split(os.pathsep):
        if not path:
            continue

        norm_path = os.path.normpath(path)
        if norm_path not in new_houdini_menu_path:
            new_houdini_menu_path.append(norm_path)

    # Add ampersand for unknown reason (Maybe is needed in Houdini?)
    new_houdini_path.append("&")
    new_houdini_menu_path.append("&")

    env["HOUDINI_PATH"] = os.pathsep.join(new_houdini_path)
    env["HOUDINI_MENU_PATH"] = os.pathsep.join(new_houdini_menu_path)
