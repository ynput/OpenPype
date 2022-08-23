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
