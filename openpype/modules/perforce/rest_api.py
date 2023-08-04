from aiohttp.web_response import Response
from openpype.lib import Logger

from openpype.modules.perforce import rest_routes
from openpype.modules.perforce.p4_client_wrapper import P4ClientWrapper



class PerforceModuleRestAPI:
    """
    REST API endpoint used for Perforce operations
    """

    def __init__(self, user_module, server_manager):
        self._log = None
        self.module = user_module
        self.server_manager = server_manager

        self.prefix = "/perforce"

        self.register()

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    def register(self):
        p4_client = P4ClientWrapper("petr_test")
        get_changelist_endpoint = rest_routes.ChangesEndpoint(p4_client)
        self.server_manager.add_route(
            "GET",
            self.prefix + "/get_changelists",
            get_changelist_endpoint.dispatch
        )

        create_or_load_openpype_changelist_endpoint = \
            rest_routes.CreateOrLoadOPChangelist(p4_client)
        self.server_manager.add_route(
            "POST",
            self.prefix + "/create_or_load_openpype_changelist",
            create_or_load_openpype_changelist_endpoint.dispatch
        )
