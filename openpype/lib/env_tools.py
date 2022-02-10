import os


def env_value_to_bool(env_key=None, value=None, default=False):
    """Convert environment variable value to boolean.

    Function is based on value of the environemt variable. Value is lowered
    so function is not case sensitive.

    Returns:
        bool: If value match to one of ["true", "yes", "1"] result if True
            but if value match to ["false", "no", "0"] result is False else
            default value is returned.
    """
    if value is None and env_key is None:
        return default

    if value is None:
        value = os.environ.get(env_key)

    if value is not None:
        value = str(value).lower()
        if value in ("true", "yes", "1", "on"):
            return True
        elif value in ("false", "no", "0", "off"):
            return False
    return default


def get_paths_from_environ(env_key=None, env_value=None, return_first=False):
    """Return existing paths from specific environment variable.

    Args:
        env_key (str): Environment key where should look for paths.
        env_value (str): Value of environment variable. Argument `env_key` is
            skipped if this argument is entered.
        return_first (bool): Return first found value or return list of found
            paths. `None` or empty list returned if nothing found.

    Returns:
        str, list, None: Result of found path/s.
    """
    existing_paths = []
    if not env_key and not env_value:
        if return_first:
            return None
        return existing_paths

    if env_value is None:
        env_value = os.environ.get(env_key) or ""

    path_items = env_value.split(os.pathsep)
    for path in path_items:
        # Skip empty string
        if not path:
            continue
        # Normalize path
        path = os.path.normpath(path)
        # Check if path exists
        if os.path.exists(path):
            # Return path if `return_first` is set to True
            if return_first:
                return path
            # Store path
            existing_paths.append(path)

    # Return None if none of paths exists
    if return_first:
        return None
    # Return all existing paths from environment variable
    return existing_paths


def get_global_environments(env=None):
    """Load global environments from Pype.

    Return prepared and parsed global environments by pype's settings. Use
    combination of "global" environments set in pype's settings and enabled
    modules.

    Args:
        env (dict, optional): Initial environments. Empty dictionary is used
            when not entered.

    Returns;
        dict of str: Loaded and processed environments.

    """
    import acre
    from openpype.modules import ModulesManager
    from openpype.settings import get_environments

    if env is None:
        env = {}

    # Get global environments from settings
    all_settings_env = get_environments()
    parsed_global_env = acre.parse(all_settings_env["global"])

    # Merge with entered environments
    merged_env = acre.append(env, parsed_global_env)

    # Get environments from Pype modules
    modules_manager = ModulesManager()

    module_envs = modules_manager.collect_global_environments()
    publish_plugin_dirs = modules_manager.collect_plugin_paths()["publish"]

    # Set pyblish plugins paths if any module want to register them
    if publish_plugin_dirs:
        publish_paths_str = os.environ.get("PYBLISHPLUGINPATH") or ""
        publish_paths = publish_paths_str.split(os.pathsep)
        _publish_paths = {
            os.path.normpath(path) for path in publish_paths if path
        }
        for path in publish_plugin_dirs:
            _publish_paths.add(os.path.normpath(path))
        module_envs["PYBLISHPLUGINPATH"] = os.pathsep.join(_publish_paths)

    # Merge environments with current environments and update values
    if module_envs:
        parsed_envs = acre.parse(module_envs)
        merged_env = acre.merge(parsed_envs, merged_env)

    return acre.compute(merged_env, cleanup=True)
