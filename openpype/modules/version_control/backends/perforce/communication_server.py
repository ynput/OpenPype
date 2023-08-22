import os
import json
import time
import subprocess
import collections
import asyncio
import logging
import socket
import threading
from queue import Queue
from contextlib import closing
import aiohttp

from aiohttp import web
from aiohttp_json_rpc import JsonRpc
from aiohttp_json_rpc.protocol import (
    encode_request, encode_error, decode_msg, JsonRpcMsgTyp
)
from aiohttp_json_rpc.exceptions import RpcError

from openpype.lib import emit_event

from openpype.modules.version_control.backends.perforce.rest_api import (
    PerforceModuleRestAPI
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


# class CommunicationWrapper:
#     # TODO add logs and exceptions
#     communicator = None
#
#     log = logging.getLogger("CommunicationWrapper")
#
#     @classmethod
#     def create_qt_communicator(cls, *args, **kwargs):
#         """Create communicator for Artist usage."""
#         communicator = QtCommunicator(*args, **kwargs)
#         cls.set_communicator(communicator)
#         return communicator
#
#     @classmethod
#     def set_communicator(cls, communicator):
#         if not cls.communicator:
#             cls.communicator = communicator
#         else:
#             cls.log.warning("Communicator was set multiple times.")
#
#     @classmethod
#     def client(cls):
#         if not cls.communicator:
#             return None
#         return cls.communicator.client()



class WebServer:
    def __init__(self):
        self.client = None

        self.loop = asyncio.new_event_loop()
        self.app = web.Application(loop=self.loop)
        # self.port = self.find_free_port()
        self.port = 64111
        self.websocket_thread = WebServerThread(
            self, self.port, loop=self.loop
        )

    @property
    def server_is_running(self):
        return self.websocket_thread.server_is_running

    def add_route(self, *args, **kwargs):
        self.app.router.add_route(*args, **kwargs)

    @staticmethod
    def find_free_port():
        with closing(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ) as sock:
            sock.bind(("", 0))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            port = sock.getsockname()[1]
        return port

    def start(self):
        rest_api = PerforceModuleRestAPI(self.app.router)
        rest_api.register()
        self.websocket_thread.start()

    def stop(self):
        try:
            if self.websocket_thread.is_running:
                log.debug("Stopping websocket server")
                self.websocket_thread.is_running = False
                self.websocket_thread.stop()
        except Exception:
            log.warning(
                "Error has happened during Killing websocket server",
                exc_info=True
            )


class WebServerThread(threading.Thread):
    """ Listener for websocket rpc requests.

        It would be probably better to "attach" this to main thread (as for
        example Harmony needs to run something on main thread), but currently
        it creates separate thread and separate asyncio event loop
    """
    def __init__(self, module, port, loop):
        super(WebServerThread, self).__init__()
        self.is_running = False
        self.server_is_running = False
        self.port = port
        self.module = module
        self.loop = loop
        self.runner = None
        self.site = None
        self.tasks = []

    def run(self):
        self.is_running = True

        try:
            log.debug("Starting websocket server")

            self.loop.run_until_complete(self.start_server())

            webserver_url = "http://localhost:{}".format(self.port)
            log.info(
                f"Running Websocket server on URL:{webserver_url}"
            )
            os.environ["PERFORCE_WEBSERVER_URL"] = webserver_url

            asyncio.ensure_future(self.check_shutdown(), loop=self.loop)

            self.server_is_running = True
            self.loop.run_forever()

        except Exception:
            log.warning(
                "Websocket Server service has failed", exc_info=True
            )
        finally:
            self.server_is_running = False
            # optional
            self.loop.close()

        self.is_running = False
        log.info("Websocket server stopped")

    async def start_server(self):
        """ Starts runner and TCPsite """
        self.runner = web.AppRunner(self.module.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "localhost", self.port)
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

        log.debug("## Server shutdown started")

        await self.site.stop()
        log.debug("# Site stopped")
        await self.runner.cleanup()
        log.debug("# Server runner stopped")
        tasks = [
            task for task in asyncio.all_tasks()
            if task is not asyncio.current_task()
        ]
        list(map(lambda task: task.cancel(), tasks))  # cancel all the tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        log.debug(f"Finished awaiting cancelled tasks, results: {results}...")
        await self.loop.shutdown_asyncgens()
        # to really make sure everything else has time to stop
        await asyncio.sleep(0.07)
        self.loop.stop()


# class BaseRpc(JsonRpc):
#     def __init__(self, communication_obj, route_name="", **kwargs):
#         super().__init__(**kwargs)
#         self.requests_ids = collections.defaultdict(lambda: 0)
#         self.waiting_requests = collections.defaultdict(list)
#         self.responses = collections.defaultdict(list)
#
#         self.route_name = route_name
#         self.communication_obj = communication_obj
#
#     async def _handle_rpc_msg(self, http_request, raw_msg):
#         # This is duplicated code from super but there is no way how to do it
#         # to be able handle server->client requests
#         host = http_request.host
#         if host in self.waiting_requests:
#             try:
#                 _raw_message = raw_msg.data
#                 msg = decode_msg(_raw_message)
#
#             except RpcError as error:
#                 await self._ws_send_str(http_request, encode_error(error))
#                 return
#
#             if msg.type in (JsonRpcMsgTyp.RESULT, JsonRpcMsgTyp.ERROR):
#                 msg_data = json.loads(_raw_message)
#                 if msg_data.get("id") in self.waiting_requests[host]:
#                     self.responses[host].append(msg_data)
#                     return
#
#         return await super()._handle_rpc_msg(http_request, raw_msg)
#
#     def client_connected(self):
#         # TODO This is poor check. Add check it is client from TVPaint
#         if self.clients:
#             return True
#         return False
#
#     def send_notification(self, client, method, params=None):
#         if params is None:
#             params = []
#         asyncio.run_coroutine_threadsafe(
#             client.ws.send_str(encode_request(method, params=params)),
#             loop=self.loop
#         )
#
#     def send_request(self, client, method, params=None, timeout=0):
#         if params is None:
#             params = {}
#
#         client_host = client.host
#
#         request_id = self.requests_ids[client_host]
#         self.requests_ids[client_host] += 1
#
#         self.waiting_requests[client_host].append(request_id)
#
#         log.debug("Sending request to client {} ({}, {}) id: {}".format(
#             client_host, method, params, request_id
#         ))
#         future = asyncio.run_coroutine_threadsafe(
#             client.ws.send_str(encode_request(method, request_id, params)),
#             loop=self.loop
#         )
#         result = future.result()
#
#         not_found = object()
#         response = not_found
#         start = time.time()
#         while True:
#             if client.ws.closed:
#                 return None
#
#             for _response in self.responses[client_host]:
#                 _id = _response.get("id")
#                 if _id == request_id:
#                     response = _response
#                     break
#
#             if response is not not_found:
#                 break
#
#             if timeout > 0 and (time.time() - start) > timeout:
#                 raise Exception("Timeout passed")
#                 return
#
#             time.sleep(0.1)
#
#         if response is not_found:
#             raise Exception("Connection closed")
#
#         self.responses[client_host].remove(response)
#
#         error = response.get("error")
#         result = response.get("result")
#         if error:
#             raise Exception("Error happened: {}".format(error))
#         return result


# class MainThreadItem:
#     """Structure to store information about callback in main thread.
#
#     Item should be used to execute callback in main thread which may be needed
#     for execution of Qt objects.
#
#     Item store callback (callable variable), arguments and keyword arguments
#     for the callback. Item hold information about it's process.
#     """
#     not_set = object()
#     sleep_time = 0.1
#
#     def __init__(self, callback, *args, **kwargs):
#         self.done = False
#         self.exception = self.not_set
#         self.result = self.not_set
#         self.callback = callback
#         self.args = args
#         self.kwargs = kwargs
#
#     def execute(self):
#         """Execute callback and store it's result.
#
#         Method must be called from main thread. Item is marked as `done`
#         when callback execution finished. Store output of callback of exception
#         information when callback raise one.
#         """
#         log.debug("Executing process in main thread")
#         if self.done:
#             log.warning("- item is already processed")
#             return
#
#         callback = self.callback
#         args = self.args
#         kwargs = self.kwargs
#         log.info("Running callback: {}".format(str(callback)))
#         try:
#             result = callback(*args, **kwargs)
#             self.result = result
#
#         except Exception as exc:
#             self.exception = exc
#
#         finally:
#             self.done = True
#
#     def wait(self):
#         """Wait for result from main thread.
#
#         This method stops current thread until callback is executed.
#
#         Returns:
#             object: Output of callback. May be any type or object.
#
#         Raises:
#             Exception: Reraise any exception that happened during callback
#                 execution.
#         """
#         while not self.done:
#             time.sleep(self.sleep_time)
#
#         if self.exception is self.not_set:
#             return self.result
#         raise self.exception
#
#     async def async_wait(self):
#         """Wait for result from main thread.
#
#         Returns:
#             object: Output of callback. May be any type or object.
#
#         Raises:
#             Exception: Reraise any exception that happened during callback
#                 execution.
#         """
#         while not self.done:
#             await asyncio.sleep(self.sleep_time)
#
#         if self.exception is self.not_set:
#             return self.result
#         raise self.exception


# class BaseCommunicator:
#     def __init__(self):
#         self.process = None
#         self.websocket_server = None
#         self.websocket_rpc = None
#         self.exit_code = None
#         self._connected_client = None
#
#     @property
#     def server_is_running(self):
#         if self.websocket_server is None:
#             return False
#         return self.websocket_server.server_is_running
#
#     def _create_routes(self):
#         # self.websocket_rpc = BaseRpc(
#         #     self, loop=self.websocket_server.loop
#         # )
#         self.websocket_server.add_route(
#             "*", "/ws", self.websocket_handler
#         )
#
#     async def websocket_handler(self, request):
#         print('Websocket connection starting')
#         ws = aiohttp.web.WebSocketResponse()
#         await ws.prepare(request)
#         print('Websocket connection ready')
#
#         async for msg in ws:
#             print(msg)
#             if msg.type == aiohttp.WSMsgType.TEXT:
#                 print(msg.data)
#                 if msg.data == 'close':
#                     await ws.close()
#                 else:
#                     await ws.send_str(msg.data + '/answer')
#
#         print('Websocket connection closed')
#         return ws
#
#     def _start_webserver(self):
#         self.websocket_server.start()
#         # Make sure RPC is using same loop as websocket server
#         while not self.websocket_server.server_is_running:
#             time.sleep(0.1)
#
#     def _stop_webserver(self):
#         self.websocket_server.stop()
#
#     def _exit(self, exit_code=None):
#         self._stop_webserver()
#         if exit_code is not None:
#             self.exit_code = exit_code
#
#         if self.exit_code is None:
#             self.exit_code = 0
#
#     def stop(self):
#         """Stop communication and currently running python process."""
#         log.info("Stopping communication")
#         self._exit()
#
#     def launch(self, launch_args):
#         """Prepare all required data and launch host.
#
#         First is prepared websocket server as communication point for host,
#         when server is ready to use host is launched as subprocess.
#         """
#         # if platform.system().lower() == "windows":
#         #     self._prepare_windows_plugin(launch_args)
#
#         # Launch TVPaint and the websocket server.
#         log.info("Launching Unreal")
#         self.websocket_server = WebServer()
#
#         self._create_routes()
#
#         os.environ["WEBSOCKET_URL"] = "ws://localhost:{}/ws".format(
#             self.websocket_server.port
#         )
#
#         log.info("Added request handler for url: {}".format(
#             os.environ["WEBSOCKET_URL"]
#         ))
#
#         self._start_webserver()
#
#         # Start TVPaint when server is running
#         # self._launch_tv_paint(launch_args)
#         self._launch_unreal(launch_args)
#
#         log.info("Waiting for client connection")
#         while True:
#             if self.process.poll() is not None:
#                 log.debug("Host process is not alive. Exiting")
#                 self._exit(1)
#                 return
#
#             if self.websocket_rpc.client_connected():
#                 log.info("Client has connected")
#                 break
#             time.sleep(0.5)
#
#         emit_event("application.launched")
#
#     def _client(self):
#         if not self.websocket_rpc:
#             log.warning("Communicator's server did not start yet.")
#             return None
#
#         for client in self.websocket_rpc.clients:
#             if not client.ws.closed:
#                 return client
#         log.warning("Client is not yet connected to Communicator.")
#         return None
#
#     def client(self):
#         if not self._connected_client or self._connected_client.ws.closed:
#             self._connected_client = self._client()
#         return self._connected_client
#
#     def send_request(self, method, params=None):
#         client = self.client()
#         if not client:
#             return
#
#         return self.websocket_rpc.send_request(
#             client, method, params
#         )
#
#     def send_notification(self, method, params=None):
#         client = self.client()
#         if not client:
#             return
#
#         self.websocket_rpc.send_notification(
#             client, method, params
#         )
