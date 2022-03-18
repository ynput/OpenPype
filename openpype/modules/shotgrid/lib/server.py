import traceback

import requests
from typing import Dict, Any, List

from openpype.api import Logger
from openpype.modules.shotgrid.lib import (
    settings as settings_lib,
)

_LOG = Logger().get_logger("ShotgridModule.server")


def find_linked_projects(email: str) -> List[Dict[str, Any]]:
    url = "".join(
        [
            settings_lib.get_leecher_backend_url(),
            "/user/",
            email,
            "/project-user-links",
        ]
    )
    try:
        return requests.get(url).json()
    except requests.exceptions.RequestException as e:
        _LOG.error(e)
        traceback.print_stack()
