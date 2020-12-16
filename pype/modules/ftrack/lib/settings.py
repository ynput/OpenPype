import os
from pype.api import (
    Logger,
    get_system_settings,
    get_default_components,
    decompose_url,
    compose_url
)

log = Logger().get_logger(__name__)


def get_ftrack_settings():
    return get_system_settings()["modules"]["ftrack"]


def get_ftrack_url_from_settings():
    return get_ftrack_settings()["ftrack_server"]


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
