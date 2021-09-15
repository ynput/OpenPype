def add_implementation_envs(env, _app):
    """Modify environments to contain all required for implementation."""
    defaults = {
        "OPENPYPE_LOG_NO_COLORS": "True",
        "WEBSOCKET_URL": "ws://localhost:8097/ws/"
    }
    for key, value in defaults.items():
        if not env.get(key):
            env[key] = value
