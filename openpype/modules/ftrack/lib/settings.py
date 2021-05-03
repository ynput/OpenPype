import os
from openpype.api import get_system_settings


def get_ftrack_settings():
    return get_system_settings()["modules"]["ftrack"]


def get_ftrack_url_from_settings():
    return get_ftrack_settings()["ftrack_server"]


def get_ftrack_event_mongo_info():
    database_name = os.environ["OPENPYPE_DATABASE_NAME"]
    collection_name = "ftrack_events"
    return database_name, collection_name
