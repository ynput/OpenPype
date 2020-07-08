from pype.api import config, Logger

import threading
from aiohttp import web, WSCloseCode
import asyncio
import weakref
from wsrpc_aiohttp import STATIC_DIR, WebSocketAsync

from . import external_app_1

log = Logger().get_logger("WebsocketServer")


class WebSocketServer():
    """
        Basic POC implementation of asychronic websocket RPC server.
        Uses class in external_app_1.py to mimic implementation for single
        external application.
        'test_client' folder contains two test implementations of client

        WIP
    """

    def __init__(self):
        self.qaction = None
        self.failed_icon = None
        self._is_running = False
        default_port = 8099

        try:
            self.presets = config.get_presets()["services"]["websocket_server"]
        except Exception:
            self.presets = {"default_port": default_port, "exclude_ports": []}
            log.debug((
                        "There are not set presets for WebsocketServer."
                        " Using defaults \"{}\""
                      ).format(str(self.presets)))

        self.app = web.Application()
        self.app["websockets"] = weakref.WeakSet()

        self.app.router.add_route("*", "/ws/", WebSocketAsync)
        self.app.router.add_static("/js", STATIC_DIR)
        self.app.router.add_static("/", ".")

        # add route with multiple methods for single "external app"
        WebSocketAsync.add_route('ExternalApp1', external_app_1.ExternalApp1)

        self.app.on_shutdown.append(self.on_shutdown)

        self.websocket_thread = WebsocketServerThread(self, default_port)

    def add_routes_for_class(self, cls):
        """ Probably obsolete, use classes inheriting from WebSocketRoute """
        methods = [method for method in dir(cls) if '__' not in method]
        log.info("added routes for {}".format(methods))
        for method in methods:
            WebSocketAsync.add_route(method, getattr(cls, method))

    def tray_start(self):
        self.websocket_thread.start()

        # log.info("Starting websocket server")
        # loop = asyncio.get_event_loop()
        # self.runner = web.AppRunner(self.app)
        # loop.run_until_complete(self.runner.setup())
        # self.site = web.TCPSite(self.runner, 'localhost', 8044)
        # loop.run_until_complete(self.site.start())
        # log.info('site {}'.format(self.site._server))
        # asyncio.ensure_future()
        # #loop.run_forever()
        # #web.run_app(self.app, port=8044)
        # log.info("Started websocket server")

    @property
    def is_running(self):
        return self.websocket_thread.is_running

    def stop(self):
        self.websocket_thread.is_running = False

    def thread_stopped(self):
        self._is_running = False

    async def on_shutdown(self):
        """
            Gracefully remove all connected websocket connections
        :return: None
        """
        log.info('Shutting down websocket server')
        for ws in set(self.app['websockets']):
            await ws.close(code=WSCloseCode.GOING_AWAY,
                           message='Server shutdown')


class WebsocketServerThread(threading.Thread):
    """ Listener for websocket rpc requests.

        It would be probably better to "attach" this to main thread (as for
        example Harmony needs to run something on main thread), but currently
        it creates separate thread and separate asyncio event loop
    """
    def __init__(self, module, port):
        super(WebsocketServerThread, self).__init__()
        self.is_running = False
        self.port = port
        self.module = module

    def run(self):
        self.is_running = True

        try:
            log.debug(
                "Running Websocket server on URL:"
                " \"ws://localhost:{}\"".format(self.port)
            )

            log.info("Starting websocket server")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            web.run_app(self.module.app, port=self.port)  # blocking
            log.info("Started websocket server")

        except Exception:
            log.warning(
                "Websocket Server service has failed", exc_info=True
            )

        self.is_running = False
        self.module.thread_stopped()
