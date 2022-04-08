from copy import copy

from avalon.api import AvalonMongoDB

from openpype.api import Logger
from openpype.modules.shotgrid.lib import (
    credentials,
    settings,
    server,
)

_LOG = Logger().get_logger("ShotgridModule.patch")


def _patched_projects(
    self, projection=None, only_active=True
):
    all_projects = list(self._prev_projects(projection, only_active))
    if (
        not credentials.get_local_login()
        or not settings.filter_projects_by_login()
    ):
        return all_projects
    try:
        linked_names = _fetch_linked_project_names() or set()
        return [x for x in all_projects if _upper(x["name"]) in linked_names]
    except Exception as e:
        print(e)
        return all_projects


def _upper(x):
    return str(x).strip().upper()


def _fetch_linked_project_names():
    return {
        _upper(x["project_name"])
        for x in server.find_linked_projects(credentials.get_local_login())
    }


def patch_avalon_db():
    _LOG.debug("Run avalon patching")
    if AvalonMongoDB.projects is _patched_projects:
        return None
    _LOG.debug("Patch Avalon.projects method")
    AvalonMongoDB._prev_projects = copy(AvalonMongoDB.projects)
    AvalonMongoDB.projects = _patched_projects
