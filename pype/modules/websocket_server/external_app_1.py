import asyncio

from pype.api import Logger
from wsrpc_aiohttp import WebSocketRoute

log = Logger().get_logger("WebsocketServer")


class ExternalApp1(WebSocketRoute):
    """
        One route, mimicking external application (like Harmony, etc).
        All functions could be called from client.
        'do_notify' function calls function on the client - mimicking
            notification after long running job on the server or similar
    """

    def init(self, **kwargs):
        # Python __init__ must be return "self".
        # This method might return anything.
        log.debug("someone called ExternalApp1 route")
        return kwargs

    async def server_function_one(self):
        log.info('In function one')

    async def server_function_two(self):
        log.info('In function two')
        return 'function two'

    async def server_function_three(self):
        log.info('In function three')
        asyncio.ensure_future(self.do_notify())
        return '{"message":"function tree"}'

    async def server_function_four(self, *args, **kwargs):
        log.info('In function four args {} kwargs {}'.format(args, kwargs))
        ret = dict(**kwargs)
        ret["message"] = "function four received arguments"
        return str(ret)

    # This method calls function on the client side
    async def do_notify(self):
        import time
        time.sleep(5)
        log.info('Calling function on server after delay')
        awesome = 'Somebody server_function_three method!'
        await self.socket.call('notify', result=awesome)
