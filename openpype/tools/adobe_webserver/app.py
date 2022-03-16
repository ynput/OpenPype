"""This Webserver tool is python 3 specific.

Don't import directly to avalon.tools or implementation of Python 2 hosts
would break.
"""
import os
import logging
import urllib
import threading
import asyncio
import socket

from aiohttp import web

from wsrpc_aiohttp import (
    WSRPCClient
)

from avalon import api

log = logging.getLogger(__name__)


class WebServerTool:
    """
        Basic POC implementation of asychronic websocket RPC server.
        Uses class in external_app_1.py to mimic implementation for single
        external application.
        'test_client' folder contains two test implementations of client
    """
    _instance = None

    def __init__(self):
        WebServerTool._instance = self

        self.client = None
        self.handlers = {}
        self.on_stop_callbacks = []

        port = None
        host_name = "localhost"
        websocket_url = os.getenv("WEBSOCKET_URL")
        if websocket_url:
            parsed = urllib.parse.urlparse(websocket_url)
            port = parsed.port
            host_name = parsed.netloc.split(":")[0]
        if not port:
            port = 8098  # fallback

        self.port = port
        self.host_name = host_name

        self.app = web.Application()

        # add route with multiple methods for single "external app"
        self.webserver_thread = WebServerThread(self, self.port)

    def add_route(self, *args, **kwargs):
        self.app.router.add_route(*args, **kwargs)

    def add_static(self, *args, **kwargs):
        self.app.router.add_static(*args, **kwargs)

    def start_server(self):
        if self.webserver_thread and not self.webserver_thread.is_alive():
            self.webserver_thread.start()

    def stop_server(self):
        self.stop()

    async def send_context_change(self, host):
        """
            Calls running webserver to inform about context change

            Used when new PS/AE should be triggered,
            but one already running, without
            this publish would point to old context.
        """
        client = WSRPCClient(os.getenv("WEBSOCKET_URL"),
                             loop=asyncio.get_event_loop())
        await client.connect()

        project = api.Session["AVALON_PROJECT"]
        asset = api.Session["AVALON_ASSET"]
        task = api.Session["AVALON_TASK"]
        log.info("Sending context change to {}-{}-{}".format(project,
                                                             asset,
                                                             task))

        await client.call('{}.set_context'.format(host),
                          project=project, asset=asset, task=task)
        await client.close()

    def port_occupied(self, host_name, port):
        """
            Check if 'url' is already occupied.

            This could mean, that app is already running and we are trying open it
            again. In that case, use existing running webserver.
            Check here is easier than capturing exception from thread.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = True
        try:
            sock.bind((host_name, port))
            result = False
        except:
            print("Port is in use")

        return result

    def call(self, func):
        log.debug("websocket.call {}".format(func))
        future = asyncio.run_coroutine_threadsafe(
            func,
            self.webserver_thread.loop
        )
        result = future.result()
        return result

    @staticmethod
    def get_instance():
        if WebServerTool._instance is None:
            WebServerTool()
        return WebServerTool._instance

    @property
    def is_running(self):
        if not self.webserver_thread:
            return False
        return self.webserver_thread.is_running

    def stop(self):
        if not self.is_running:
            return
        try:
            log.debug("Stopping websocket server")
            self.webserver_thread.is_running = False
            self.webserver_thread.stop()
        except Exception:
            log.warning(
                "Error has happened during Killing websocket server",
                exc_info=True
            )

    def thread_stopped(self):
        for callback in self.on_stop_callbacks:
            callback()


class WebServerThread(threading.Thread):
    """ Listener for websocket rpc requests.

        It would be probably better to "attach" this to main thread (as for
        example Harmony needs to run something on main thread), but currently
        it creates separate thread and separate asyncio event loop
    """
    def __init__(self, module, port):
        super(WebServerThread, self).__init__()

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
            log.info("Starting web server")
            self.loop = asyncio.new_event_loop()  # create new loop for thread
            asyncio.set_event_loop(self.loop)

            self.loop.run_until_complete(self.start_server())

            websocket_url = "ws://localhost:{}/ws".format(self.port)

            log.debug(
                "Running Websocket server on URL: \"{}\"".format(websocket_url)
            )

            asyncio.ensure_future(self.check_shutdown(), loop=self.loop)
            self.loop.run_forever()
        except Exception:
            self.is_running = False
            log.warning(
                "Websocket Server service has failed", exc_info=True
            )
            raise
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
