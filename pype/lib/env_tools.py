import os


def env_value_to_bool(env_key=None, value=None, default=False):
    if value is None and env_key is None:
        return default

    if value is None:
        value = os.environ.get(env_key)

    if value is not None:
        value = str(value).lower()
        if value in ("true", "yes", "1"):
            return True
        elif value in ("false", "no", "0"):
            return False
    return default
