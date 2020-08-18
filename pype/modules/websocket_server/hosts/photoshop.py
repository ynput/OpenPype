import asyncio

from pype.api import Logger
from wsrpc_aiohttp import WebSocketRoute

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
        log.debug("photoshop.read client calls server server calls Photo client")
        return await self.socket.call('Photoshop.read')
