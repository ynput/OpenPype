from openpype.settings import get_system_settings, get_project_settings
from openpype.modules.shotgrid.lib.const import MODULE_NAME


def get_shotgrid_project_settings(project):
    return get_project_settings(project).get(MODULE_NAME, {})


def get_shotgrid_settings():
    return get_system_settings().get("modules", {}).get(MODULE_NAME, {})


def get_shotgrid_servers():
    return get_shotgrid_settings().get("shotgrid_settings", {})


def get_leecher_backend_url():
    return get_shotgrid_settings().get("leecher_backend_url")
