from pype.api import Logger
from wsrpc_aiohttp import WebSocketRoute
import functools

import avalon.photoshop as photoshop

log = Logger().get_logger("WebsocketServer")


class Photoshop(WebSocketRoute):
    """
        One route, mimicking external application (like Harmony, etc).
        All functions could be called from client.
        'do_notify' function calls function on the client - mimicking
            notification after long running job on the server or similar
    """
    instance = None

    def init(self, **kwargs):
        # Python __init__ must be return "self".
        # This method might return anything.
        log.debug("someone called Photoshop route")
        self.instance = self
        return kwargs

    # server functions
    async def ping(self):
        log.debug("someone called Photoshop route ping")

    # This method calls function on the client side
    # client functions

    async def read(self):
        log.debug("photoshop.read client calls server server calls "
                  "Photo client")
        return await self.socket.call('Photoshop.read')

    # panel routes for tools
    async def creator_route(self):
        self._tool_route("creator")

    async def workfiles_route(self):
        self._tool_route("workfiles")

    async def loader_route(self):
        self._tool_route("loader")

    async def publish_route(self):
        self._tool_route("publish")

    async def sceneinventory_route(self):
        self._tool_route("sceneinventory")

    async def projectmanager_route(self):
        self._tool_route("projectmanager")

    def _tool_route(self, tool_name):
        """The address accessed when clicking on the buttons."""
        partial_method = functools.partial(photoshop.show, tool_name)

        photoshop.execute_in_main_thread(partial_method)

        # Required return statement.
        return "nothing"
