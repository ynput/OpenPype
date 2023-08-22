from aiohttp.web_response import Response
from openpype.lib import Logger

from openpype.modules.version_control.backends.perforce import rest_routes


class PerforceModuleRestAPI:
    """
    REST API endpoint used for Perforce operations
    """

    def __init__(self, server_manager):
        self._log = None
        self.server_manager = server_manager
        self.prefix = "/perforce"

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    def register(self):
        add_file = rest_routes.AddEndpoint()
        self.server_manager.add_route(
            "POST",
            self.prefix + "/add_file",
            add_file.dispatch
        )

        checkout = rest_routes.CheckoutEndpoint()
        self.server_manager.add_route(
            "POST",
            self.prefix + "/checkout",
            checkout.dispatch
        )

        submit_change_list = rest_routes.SubmitChangelist()
        self.server_manager.add_route(
            "POST",
            self.prefix + "/submit_change_list",
            submit_change_list.dispatch
        )
