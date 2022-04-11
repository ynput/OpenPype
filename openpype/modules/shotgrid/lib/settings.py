import os

from pymongo import MongoClient
from openpype.api import get_system_settings, get_project_settings
from openpype.modules.shotgrid.lib.const import MODULE_NAME
from openpype.modules.shotgrid.lib.tools import memoize


def get_project_list():
    mongo_url = os.getenv("OPENPYPE_MONGO")
    client = MongoClient(mongo_url)
    db = client['avalon']
    return db.list_collection_names()


@memoize
def get_shotgrid_project_settings(project):
    return get_project_settings(project).get(MODULE_NAME, {})


@memoize
def get_shotgrid_settings():
    return get_system_settings().get("modules", {}).get(MODULE_NAME, {})


def get_shotgrid_servers():
    return get_shotgrid_settings().get("shotgrid_settings", {})


def get_leecher_backend_url():
    return get_shotgrid_settings().get("leecher_backend_url")


def filter_projects_by_login():
    return bool(get_shotgrid_settings().get("filter_projects_by_login", False))


def get_shotgrid_event_mongo_info():
    database_name = os.environ["OPENPYPE_DATABASE_NAME"]
    collection_name = "shotgrid_events"
    return database_name, collection_name
