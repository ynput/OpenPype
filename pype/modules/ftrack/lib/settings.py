import os
from pype.api import (
    Logger,
    get_system_settings
)


log = Logger().get_logger("ftrack_server.lib")

FTRACK_MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HANDLERS_DIR = os.path.join(FTRACK_MODULE_DIR, "events")
USER_HANDLERS_DIR = os.path.join(FTRACK_MODULE_DIR, "actions")


def get_ftrack_url_from_settings():
    ftrack_url = (
        get_system_settings()
        ["modules"]
        ["Ftrack"]
        ["ftrack_server"]
    )
    return ftrack_url


def get_server_event_handler_paths():
    paths = []
    # Environment variable overrides settings
    if "FTRACK_EVENTS_PATH" in os.environ:
        env_paths = os.environ.get("FTRACK_EVENTS_PATH")
        paths.extend(env_paths.split(os.pathsep))
        return paths

    # Add pype's default dir
    paths.append(SERVER_HANDLERS_DIR)
    # Add additional paths from settings
    paths.extend(
        get_system_settings()
        ["modules"]
        ["Ftrack"]
        ["ftrack_events_path"]
    )
    try:
        clockify_path = clockify_event_path()
        if clockify_path:
            paths.append(clockify_path)
    except Exception:
        log.warning("Clockify paths function failed.", exc_info=True)

    # Filter only existing paths
    _paths = []
    for path in paths:
        if os.path.exists(path):
            _paths.append(path)
        else:
            log.warning((
                "Registered event handler path is not accessible: {}"
            ).format(path))
    return _paths


def get_user_event_handler_paths():
    paths = []
    # Add pype's default dir
    paths.append(USER_HANDLERS_DIR)
    # Add additional paths from settings
    paths.extend(
        get_system_settings()
        ["modules"]
        ["Ftrack"]
        ["ftrack_actions_path"]
    )

    # Filter only existing paths
    _paths = []
    for path in paths:
        if os.path.exists(path):
            _paths.append(path)
        else:
            log.warning((
                "Registered event handler path is not accessible: {}"
            ).format(path))
    return _paths


def clockify_event_path():
    api_key = os.environ.get("CLOCKIFY_API_KEY")
    if not api_key:
        log.warning("Clockify API key is not set.")
        return

    workspace_name = os.environ.get("CLOCKIFY_WORKSPACE")
    if not workspace_name:
        log.warning("Clockify Workspace is not set.")
        return

    from pype.modules.clockify.constants import CLOCKIFY_FTRACK_SERVER_PATH

    return CLOCKIFY_FTRACK_SERVER_PATH
