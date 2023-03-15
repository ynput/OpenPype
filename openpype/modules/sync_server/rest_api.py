from aiohttp.web_response import Response
from openpype.lib import Logger


class SyncServerModuleRestApi:
    """
    REST API endpoint used for calling from hosts when context change
    happens in Workfile app.
    """

    def __init__(self, user_module, server_manager):
        self._log = None
        self.module = user_module
        self.server_manager = server_manager

        self.prefix = "/sync_server"

        self.register()

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    def register(self):
        self.server_manager.add_route(
            "POST",
            self.prefix + "/reset_timer",
            self.reset_timer,
        )

    async def reset_timer(self, _request):
        """Force timer to run immediately."""
        self.module.reset_timer()

        return Response(status=200)
