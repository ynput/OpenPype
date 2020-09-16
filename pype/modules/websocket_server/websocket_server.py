from pype.api import Logger

import threading
from aiohttp import web
import asyncio
from wsrpc_aiohttp import STATIC_DIR, WebSocketAsync

import os
import sys
import pyclbr
import importlib
import urllib

log = Logger().get_logger("WebsocketServer")


class WebSocketServer():
    """
        Basic POC implementation of asychronic websocket RPC server.
        Uses class in external_app_1.py to mimic implementation for single
        external application.
        'test_client' folder contains two test implementations of client
    """
    _instance = None

    def __init__(self):
        self.qaction = None
        self.failed_icon = None
        self._is_running = False
        WebSocketServer._instance = self
        self.client = None
        self.handlers = {}

        websocket_url = os.getenv("WEBSOCKET_URL")
        if websocket_url:
            parsed = urllib.parse.urlparse(websocket_url)
            port = parsed.port
        if not port:
            port = 8099  # fallback

        self.app = web.Application()

        self.app.router.add_route("*", "/ws/", WebSocketAsync)
        self.app.router.add_static("/js", STATIC_DIR)
        self.app.router.add_static("/", ".")

        # add route with multiple methods for single "external app"
        directories_with_routes = ['hosts']
        self.add_routes_for_directories(directories_with_routes)

        self.websocket_thread = WebsocketServerThread(self, port)

    def add_routes_for_directories(self, directories_with_routes):
        """ Loops through selected directories to find all modules and
            in them all classes implementing 'WebSocketRoute' that could be
            used as route.
            All methods in these classes are registered automatically.
        """
        for dir_name in directories_with_routes:
            dir_name = os.path.join(os.path.dirname(__file__), dir_name)
            for file_name in os.listdir(dir_name):
                if '.py' in file_name and '__' not in file_name:
                    self.add_routes_for_module(file_name, dir_name)

    def add_routes_for_module(self, file_name, dir_name):
        """ Auto routes for all classes implementing 'WebSocketRoute'
            in 'file_name' in 'dir_name'
        """
        module_name = file_name.replace('.py', '')
        module_info = pyclbr.readmodule(module_name, [dir_name])

        for class_name, cls_object in module_info.items():
            sys.path.append(dir_name)
            if 'WebSocketRoute' in cls_object.super:
                log.debug('Adding route for {}'.format(class_name))
                module = importlib.import_module(module_name)
                cls = getattr(module, class_name)
                WebSocketAsync.add_route(class_name, cls)
            sys.path.pop()

    def call(self, func):
        log.debug("websocket.call {}".format(func))
        future = asyncio.run_coroutine_threadsafe(func,
                                                  self.websocket_thread.loop)
        result = future.result()
        return result

    def get_client(self):
        """
            Return first connected client to WebSocket
            TODO implement selection by Route
        :return: <WebSocketAsync> client
        """
        clients = WebSocketAsync.get_clients()
        client = None
        if len(clients) > 0:
            key = list(clients.keys())[0]
            client = clients.get(key)

        return client

    @staticmethod
    def get_instance():
        if WebSocketServer._instance is None:
            WebSocketServer()
        return WebSocketServer._instance

    def tray_start(self):
        self.websocket_thread.start()

    def tray_exit(self):
        self.stop()

    def stop_websocket_server(self):

        self.stop()

    @property
    def is_running(self):
        return self.websocket_thread.is_running

    def stop(self):
        if not self.is_running:
            return
        try:
            log.debug("Stopping websocket server")
            self.websocket_thread.is_running = False
            self.websocket_thread.stop()
        except Exception:
            log.warning(
                "Error has happened during Killing websocket server",
                exc_info=True
            )

    def thread_stopped(self):
        self._is_running = False


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
        self.loop = None
        self.runner = None
        self.site = None
        self.tasks = []

    def run(self):
        self.is_running = True

        try:
            log.info("Starting websocket server")
            self.loop = asyncio.new_event_loop()  # create new loop for thread
            asyncio.set_event_loop(self.loop)

            self.loop.run_until_complete(self.start_server())

            log.debug(
                "Running Websocket server on URL:"
                " \"ws://localhost:{}\"".format(self.port)
            )

            asyncio.ensure_future(self.check_shutdown(), loop=self.loop)
            self.loop.run_forever()
        except Exception:
            log.warning(
                "Websocket Server service has failed", exc_info=True
            )
        finally:
            self.loop.close()  # optional

        self.is_running = False
        self.module.thread_stopped()
        log.info("Websocket server stopped")

    async def start_server(self):
        """ Starts runner and TCPsite """
        self.runner = web.AppRunner(self.module.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, 'localhost', self.port)
        await self.site.start()

    def stop(self):
        """Sets is_running flag to false, 'check_shutdown' shuts server down"""
        self.is_running = False

    async def check_shutdown(self):
        """ Future that is running and checks if server should be running
            periodically.
        """
        while self.is_running:
            while self.tasks:
                task = self.tasks.pop(0)
                log.debug("waiting for task {}".format(task))
                await task
                log.debug("returned value {}".format(task.result))

            await asyncio.sleep(0.5)

        log.debug("Starting shutdown")
        await self.site.stop()
        log.debug("Site stopped")
        await self.runner.cleanup()
        log.debug("Runner stopped")
        tasks = [task for task in asyncio.all_tasks() if
                 task is not asyncio.current_task()]
        list(map(lambda task: task.cancel(), tasks))  # cancel all the tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        log.debug(f'Finished awaiting cancelled tasks, results: {results}...')
        await self.loop.shutdown_asyncgens()
        # to really make sure everything else has time to stop
        await asyncio.sleep(0.07)
        self.loop.stop()
