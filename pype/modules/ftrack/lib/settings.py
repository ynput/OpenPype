import os
from pype.api import (
    Logger,
    get_system_settings,
    get_default_components,
    decompose_url,
    compose_url
)

log = Logger().get_logger(__name__)

FTRACK_MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HANDLERS_DIR = os.path.join(FTRACK_MODULE_DIR, "events")
USER_HANDLERS_DIR = os.path.join(FTRACK_MODULE_DIR, "actions")


def get_ftrack_settings():
    return get_system_settings()["modules"]["Ftrack"]


def get_ftrack_url_from_settings():
    return get_ftrack_settings()["ftrack_server"]


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
        get_ftrack_settings()["ftrack_events_path"]
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
        get_ftrack_settings()["ftrack_actions_path"]
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


def get_ftrack_event_mongo_info():
    ftrack_settings = get_ftrack_settings()
    database_name = ftrack_settings["mongo_database_name"]
    collection_name = ftrack_settings["mongo_collection_name"]

    # TODO add possibility to set in settings and use PYPE_MONGO_URL if not set
    mongo_url = os.environ.get("FTRACK_EVENTS_MONGO_URL")
    if mongo_url is not None:
        components = decompose_url(mongo_url)
    else:
        components = get_default_components()

    uri = compose_url(**components)

    return uri, components["port"], database_name, collection_name
