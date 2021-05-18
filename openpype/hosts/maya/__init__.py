import os


def add_implementation_envs(env):
    # Add requirements to PYTHONPATH
    pype_root = os.environ["OPENPYPE_REPOS_ROOT"]
    new_python_paths = [
        os.path.join(pype_root, "openpype", "hosts", "maya", "startup"),
        os.path.join(pype_root, "repos", "avalon-core", "setup", "maya"),
        os.path.join(pype_root, "tools", "mayalookassigner")
    ]
    old_python_path = env.get("PYTHONPATH") or ""
    for path in old_python_path.split(os.pathsep):
        if not path or not os.path.exists(path):
            continue

        norm_path = os.path.normpath(path)
        if norm_path not in new_python_paths:
            new_python_paths.append(norm_path)

    env["PYTHONPATH"] = os.pathsep.join(new_python_paths)

    # Set default values if are not already set via settings
    defaults = {
        "MAYA_DISABLE_CLIC_IPM": "Yes",
        "MAYA_DISABLE_CIP": "Yes",
        "MAYA_DISABLE_CER": "Yes",
        "PYMEL_SKIP_MEL_INIT": "Yes",
        "LC_ALL": "C",
        "OPENPYPE_LOG_NO_COLORS": "Yes"
    }
    for key, value in defaults.items():
        if not env.get(key):
            env[key] = value
