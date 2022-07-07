import os
from pprint import pformat
from openpype.api import get_project_settings, Logger

log = Logger.get_logger(__name__)


def CreateEditorial():
    from openpype.hosts.traypublisher.api.plugin import EditorialCreator

    project_name = os.environ["AVALON_PROJECT"]
    project_settings = get_project_settings(project_name)

    editorial_creators = project_settings["traypublisher"]["editorial_creators"]

    global_variables = globals()
    for item in editorial_creators:

        log.debug(pformat(item))

        dynamic_plugin = EditorialCreator.from_settings(item)
        global_variables[dynamic_plugin.__name__] = dynamic_plugin


CreateEditorial()
