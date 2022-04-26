import os
import json
import time
import subprocess
import collections
import asyncio
import logging
import socket
import platform
import filecmp
import tempfile
import threading
import shutil
from queue import Queue
from contextlib import closing

from aiohttp import web
from aiohttp_json_rpc import JsonRpc
from aiohttp_json_rpc.protocol import (
    encode_request, encode_error, decode_msg, JsonRpcMsgTyp
)
from aiohttp_json_rpc.exceptions import RpcError

from openpype.lib import emit_event
from openpype.hosts.tvpaint.tvpaint_plugin import get_plugin_files_path

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class CommunicationWrapper:
    # TODO add logs and exceptions
    communicator = None

    log = logging.getLogger("CommunicationWrapper")

    @classmethod
    def create_qt_communicator(cls, *args, **kwargs):
        """Create communicator for Artist usage."""
        communicator = QtCommunicator(*args, **kwargs)
        cls.set_communicator(communicator)
        return communicator

    @classmethod
    def set_communicator(cls, communicator):
        if not cls.communicator:
            cls.communicator = communicator
        else:
            cls.log.warning("Communicator was set multiple times.")

    @classmethod
    def client(cls):
        if not cls.communicator:
            return None
        return cls.communicator.client()

    @classmethod
    def execute_george(cls, george_script):
        """Execute passed goerge script in TVPaint."""
        if not cls.communicator:
            return
        return cls.communicator.execute_george(george_script)


class WebSocketServer:
    def __init__(self):
        self.client = None

        self.loop = asyncio.new_event_loop()
        self.app = web.Application(loop=self.loop)
        self.port = self.find_free_port()
        self.websocket_thread = WebsocketServerThread(
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


class WebsocketServerThread(threading.Thread):
    """ Listener for websocket rpc requests.

        It would be probably better to "attach" this to main thread (as for
        example Harmony needs to run something on main thread), but currently
        it creates separate thread and separate asyncio event loop
    """
    def __init__(self, module, port, loop):
        super(WebsocketServerThread, self).__init__()
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

            log.info(
                "Running Websocket server on URL:"
                " \"ws://localhost:{}\"".format(self.port)
            )

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


class BaseTVPaintRpc(JsonRpc):
    def __init__(self, communication_obj, route_name="", **kwargs):
        super().__init__(**kwargs)
        self.requests_ids = collections.defaultdict(lambda: 0)
        self.waiting_requests = collections.defaultdict(list)
        self.responses = collections.defaultdict(list)

        self.route_name = route_name
        self.communication_obj = communication_obj

    async def _handle_rpc_msg(self, http_request, raw_msg):
        # This is duplicated code from super but there is no way how to do it
        # to be able handle server->client requests
        host = http_request.host
        if host in self.waiting_requests:
            try:
                _raw_message = raw_msg.data
                msg = decode_msg(_raw_message)

            except RpcError as error:
                await self._ws_send_str(http_request, encode_error(error))
                return

            if msg.type in (JsonRpcMsgTyp.RESULT, JsonRpcMsgTyp.ERROR):
                msg_data = json.loads(_raw_message)
                if msg_data.get("id") in self.waiting_requests[host]:
                    self.responses[host].append(msg_data)
                    return

        return await super()._handle_rpc_msg(http_request, raw_msg)

    def client_connected(self):
        # TODO This is poor check. Add check it is client from TVPaint
        if self.clients:
            return True
        return False

    def send_notification(self, client, method, params=None):
        if params is None:
            params = []
        asyncio.run_coroutine_threadsafe(
            client.ws.send_str(encode_request(method, params=params)),
            loop=self.loop
        )

    def send_request(self, client, method, params=None, timeout=0):
        if params is None:
            params = []

        client_host = client.host

        request_id = self.requests_ids[client_host]
        self.requests_ids[client_host] += 1

        self.waiting_requests[client_host].append(request_id)

        log.debug("Sending request to client {} ({}, {}) id: {}".format(
            client_host, method, params, request_id
        ))
        future = asyncio.run_coroutine_threadsafe(
            client.ws.send_str(encode_request(method, request_id, params)),
            loop=self.loop
        )
        result = future.result()

        not_found = object()
        response = not_found
        start = time.time()
        while True:
            if client.ws.closed:
                return None

            for _response in self.responses[client_host]:
                _id = _response.get("id")
                if _id == request_id:
                    response = _response
                    break

            if response is not not_found:
                break

            if timeout > 0 and (time.time() - start) > timeout:
                raise Exception("Timeout passed")
                return

            time.sleep(0.1)

        if response is not_found:
            raise Exception("Connection closed")

        self.responses[client_host].remove(response)

        error = response.get("error")
        result = response.get("result")
        if error:
            raise Exception("Error happened: {}".format(error))
        return result


class QtTVPaintRpc(BaseTVPaintRpc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from openpype.tools.utils import host_tools
        self.tools_helper = host_tools.HostToolsHelper()

        route_name = self.route_name

        # Register methods
        self.add_methods(
            (route_name, self.workfiles_tool),
            (route_name, self.loader_tool),
            (route_name, self.creator_tool),
            (route_name, self.subset_manager_tool),
            (route_name, self.publish_tool),
            (route_name, self.scene_inventory_tool),
            (route_name, self.library_loader_tool),
            (route_name, self.experimental_tools)
        )

    # Panel routes for tools
    async def workfiles_tool(self):
        log.info("Triggering Workfile tool")
        item = MainThreadItem(self.tools_helper.show_workfiles)
        self._execute_in_main_thread(item)
        return

    async def loader_tool(self):
        log.info("Triggering Loader tool")
        item = MainThreadItem(self.tools_helper.show_loader)
        self._execute_in_main_thread(item)
        return

    async def creator_tool(self):
        log.info("Triggering Creator tool")
        item = MainThreadItem(self.tools_helper.show_creator)
        await self._async_execute_in_main_thread(item, wait=False)

    async def subset_manager_tool(self):
        log.info("Triggering Subset Manager tool")
        item = MainThreadItem(self.tools_helper.show_subset_manager)
        # Do not wait for result of callback
        self._execute_in_main_thread(item, wait=False)
        return

    async def publish_tool(self):
        log.info("Triggering Publish tool")
        item = MainThreadItem(self.tools_helper.show_publish)
        self._execute_in_main_thread(item)
        return

    async def scene_inventory_tool(self):
        """Open Scene Inventory tool.

        Function can't confirm if tool was opened becauise one part of
        SceneInventory initialization is calling websocket request to host but
        host can't response because is waiting for response from this call.
        """
        log.info("Triggering Scene inventory tool")
        item = MainThreadItem(self.tools_helper.show_scene_inventory)
        # Do not wait for result of callback
        self._execute_in_main_thread(item, wait=False)
        return

    async def library_loader_tool(self):
        log.info("Triggering Library loader tool")
        item = MainThreadItem(self.tools_helper.show_library_loader)
        self._execute_in_main_thread(item)
        return

    async def experimental_tools(self):
        log.info("Triggering Library loader tool")
        item = MainThreadItem(self.tools_helper.show_experimental_tools_dialog)
        self._execute_in_main_thread(item)
        return

    async def _async_execute_in_main_thread(self, item, **kwargs):
        await self.communication_obj.async_execute_in_main_thread(
            item, **kwargs
        )

    def _execute_in_main_thread(self, item, **kwargs):
        return self.communication_obj.execute_in_main_thread(item, **kwargs)


class MainThreadItem:
    """Structure to store information about callback in main thread.

    Item should be used to execute callback in main thread which may be needed
    for execution of Qt objects.

    Item store callback (callable variable), arguments and keyword arguments
    for the callback. Item hold information about it's process.
    """
    not_set = object()
    sleep_time = 0.1

    def __init__(self, callback, *args, **kwargs):
        self.done = False
        self.exception = self.not_set
        self.result = self.not_set
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def execute(self):
        """Execute callback and store it's result.

        Method must be called from main thread. Item is marked as `done`
        when callback execution finished. Store output of callback of exception
        information when callback raise one.
        """
        log.debug("Executing process in main thread")
        if self.done:
            log.warning("- item is already processed")
            return

        callback = self.callback
        args = self.args
        kwargs = self.kwargs
        log.info("Running callback: {}".format(str(callback)))
        try:
            result = callback(*args, **kwargs)
            self.result = result

        except Exception as exc:
            self.exception = exc

        finally:
            self.done = True

    def wait(self):
        """Wait for result from main thread.

        This method stops current thread until callback is executed.

        Returns:
            object: Output of callback. May be any type or object.

        Raises:
            Exception: Reraise any exception that happened during callback
                execution.
        """
        while not self.done:
            time.sleep(self.sleep_time)

        if self.exception is self.not_set:
            return self.result
        raise self.exception

    async def async_wait(self):
        """Wait for result from main thread.

        Returns:
            object: Output of callback. May be any type or object.

        Raises:
            Exception: Reraise any exception that happened during callback
                execution.
        """
        while not self.done:
            await asyncio.sleep(self.sleep_time)

        if self.exception is self.not_set:
            return self.result
        raise self.exception


class BaseCommunicator:
    def __init__(self):
        self.process = None
        self.websocket_server = None
        self.websocket_rpc = None
        self.exit_code = None
        self._connected_client = None

    @property
    def server_is_running(self):
        if self.websocket_server is None:
            return False
        return self.websocket_server.server_is_running

    def _windows_file_process(self, src_dst_mapping, to_remove):
        """Windows specific file processing asking for admin permissions.

        It is required to have administration permissions to modify plugin
        files in TVPaint installation folder.

        Method requires `pywin32` python module.

        Args:
            src_dst_mapping (list, tuple, set): Mapping of source file to
                destination. Both must be full path. Each item must be iterable
                of size 2 `(C:/src/file.dll, C:/dst/file.dll)`.
            to_remove (list): Fullpath to files that should be removed.
        """

        import pythoncom
        from win32comext.shell import shell

        # Create temp folder where plugin files are temporary copied
        # - reason is that copy to TVPaint requires administartion permissions
        #   but admin may not have access to source folder
        tmp_dir = os.path.normpath(
            tempfile.mkdtemp(prefix="tvpaint_copy_")
        )

        # Copy source to temp folder and create new mapping
        dst_folders = collections.defaultdict(list)
        new_src_dst_mapping = []
        for old_src, dst in src_dst_mapping:
            new_src = os.path.join(tmp_dir, os.path.split(old_src)[1])
            shutil.copy(old_src, new_src)
            new_src_dst_mapping.append((new_src, dst))

        for src, dst in new_src_dst_mapping:
            src = os.path.normpath(src)
            dst = os.path.normpath(dst)
            dst_filename = os.path.basename(dst)
            dst_folder_path = os.path.dirname(dst)
            dst_folders[dst_folder_path].append((dst_filename, src))

        # create an instance of IFileOperation
        fo = pythoncom.CoCreateInstance(
            shell.CLSID_FileOperation,
            None,
            pythoncom.CLSCTX_ALL,
            shell.IID_IFileOperation
        )
        # Add delete command to file operation object
        for filepath in to_remove:
            item = shell.SHCreateItemFromParsingName(
                filepath, None, shell.IID_IShellItem
            )
            fo.DeleteItem(item)

        # here you can use SetOperationFlags, progress Sinks, etc.
        for folder_path, items in dst_folders.items():
            # create an instance of IShellItem for the target folder
            folder_item = shell.SHCreateItemFromParsingName(
                folder_path, None, shell.IID_IShellItem
            )
            for _dst_filename, source_file_path in items:
                # create an instance of IShellItem for the source item
                copy_item = shell.SHCreateItemFromParsingName(
                    source_file_path, None, shell.IID_IShellItem
                )
                # queue the copy operation
                fo.CopyItem(copy_item, folder_item, _dst_filename, None)

        # commit
        fo.PerformOperations()

        # Remove temp folder
        shutil.rmtree(tmp_dir)

    def _prepare_windows_plugin(self, launch_args):
        """Copy plugin to TVPaint plugins and set PATH to dependencies.

        Check if plugin in TVPaint's plugins exist and match to plugin
        version to current implementation version. Based on 64-bit or 32-bit
        version of the plugin. Path to libraries required for plugin is added
        to PATH variable.
        """

        host_executable = launch_args[0]
        executable_file = os.path.basename(host_executable)
        if "64bit" in executable_file:
            subfolder = "windows_x64"
        elif "32bit" in executable_file:
            subfolder = "windows_x86"
        else:
            raise ValueError(
                "Can't determine if executable "
                "leads to 32-bit or 64-bit TVPaint!"
            )

        plugin_files_path = get_plugin_files_path()
        # Folder for right windows plugin files
        source_plugins_dir = os.path.join(plugin_files_path, subfolder)

        # Path to libraries (.dll) required for plugin library
        # - additional libraries can be copied to TVPaint installation folder
        #   (next to executable) or added to PATH environment variable
        additional_libs_folder = os.path.join(
            source_plugins_dir,
            "additional_libraries"
        )
        additional_libs_folder = additional_libs_folder.replace("\\", "/")
        if (
            os.path.exists(additional_libs_folder)
            and additional_libs_folder not in os.environ["PATH"]
        ):
            os.environ["PATH"] += (os.pathsep + additional_libs_folder)

        # Path to TVPaint's plugins folder (where we want to add our plugin)
        host_plugins_path = os.path.join(
            os.path.dirname(host_executable),
            "plugins"
        )

        # Files that must be copied to TVPaint's plugin folder
        plugin_dir = os.path.join(source_plugins_dir, "plugin")

        to_copy = []
        to_remove = []
        # Remove old plugin name
        deprecated_filepath = os.path.join(
            host_plugins_path, "AvalonPlugin.dll"
        )
        if os.path.exists(deprecated_filepath):
            to_remove.append(deprecated_filepath)

        for filename in os.listdir(plugin_dir):
            src_full_path = os.path.join(plugin_dir, filename)
            dst_full_path = os.path.join(host_plugins_path, filename)
            if dst_full_path in to_remove:
                to_remove.remove(dst_full_path)

            if (
                not os.path.exists(dst_full_path)
                or not filecmp.cmp(src_full_path, dst_full_path)
            ):
                to_copy.append((src_full_path, dst_full_path))

        # Skip copy if everything is done
        if not to_copy and not to_remove:
            return

        # Try to copy
        try:
            self._windows_file_process(to_copy, to_remove)
        except Exception:
            log.error("Plugin copy failed", exc_info=True)

        # Validate copy was done
        invalid_copy = []
        for src, dst in to_copy:
            if not os.path.exists(dst) or not filecmp.cmp(src, dst):
                invalid_copy.append((src, dst))

        # Validate delete was dones
        invalid_remove = []
        for filepath in to_remove:
            if os.path.exists(filepath):
                invalid_remove.append(filepath)

        if not invalid_remove and not invalid_copy:
            return

        msg_parts = []
        if invalid_remove:
            msg_parts.append(
                "Failed to remove files: {}".format(", ".join(invalid_remove))
            )

        if invalid_copy:
            _invalid = [
                "\"{}\" -> \"{}\"".format(src, dst)
                for src, dst in invalid_copy
            ]
            msg_parts.append(
                "Failed to copy files: {}".format(", ".join(_invalid))
            )
        raise RuntimeError(" & ".join(msg_parts))

    def _launch_tv_paint(self, launch_args):
        flags = (
            subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        env = os.environ.copy()
        # Remove QuickTime from PATH on windows
        # - quicktime overrides TVPaint's ffmpeg encode/decode which may
        #   cause issues on loading
        if platform.system().lower() == "windows":
            new_path = []
            for path in env["PATH"].split(os.pathsep):
                if path and "quicktime" not in path.lower():
                    new_path.append(path)
            env["PATH"] = os.pathsep.join(new_path)

        kwargs = {
            "env": env,
            "creationflags": flags
        }
        self.process = subprocess.Popen(launch_args, **kwargs)

    def _create_routes(self):
        self.websocket_rpc = BaseTVPaintRpc(
            self, loop=self.websocket_server.loop
        )
        self.websocket_server.add_route(
            "*", "/", self.websocket_rpc.handle_request
        )

    def _start_webserver(self):
        self.websocket_server.start()
        # Make sure RPC is using same loop as websocket server
        while not self.websocket_server.server_is_running:
            time.sleep(0.1)

    def _stop_webserver(self):
        self.websocket_server.stop()

    def _exit(self, exit_code=None):
        self._stop_webserver()
        if exit_code is not None:
            self.exit_code = exit_code

    def stop(self):
        """Stop communication and currently running python process."""
        log.info("Stopping communication")
        self._exit()

    def launch(self, launch_args):
        """Prepare all required data and launch host.

        First is prepared websocket server as communication point for host,
        when server is ready to use host is launched as subprocess.
        """
        if platform.system().lower() == "windows":
            self._prepare_windows_plugin(launch_args)

        # Launch TVPaint and the websocket server.
        log.info("Launching TVPaint")
        self.websocket_server = WebSocketServer()

        self._create_routes()

        os.environ["WEBSOCKET_URL"] = "ws://localhost:{}".format(
            self.websocket_server.port
        )

        log.info("Added request handler for url: {}".format(
            os.environ["WEBSOCKET_URL"]
        ))

        self._start_webserver()

        # Start TVPaint when server is running
        self._launch_tv_paint(launch_args)

        log.info("Waiting for client connection")
        while True:
            if self.process.poll() is not None:
                log.debug("Host process is not alive. Exiting")
                self._exit(1)
                return

            if self.websocket_rpc.client_connected():
                log.info("Client has connected")
                break
            time.sleep(0.5)

        self._on_client_connect()

        emit_event("application.launched")

    def _on_client_connect(self):
        self._initial_textfile_write()

    def _initial_textfile_write(self):
        """Show popup about Write to file at start of TVPaint."""
        tmp_file = tempfile.NamedTemporaryFile(
            mode="w", prefix="a_tvp_", suffix=".txt", delete=False
        )
        tmp_file.close()
        tmp_filepath = tmp_file.name.replace("\\", "/")
        george_script = (
            "tv_writetextfile \"strict\" \"append\" \"{}\" \"empty\""
        ).format(tmp_filepath)

        result = CommunicationWrapper.execute_george(george_script)

        # Remote the file
        os.remove(tmp_filepath)

        if result is None:
            log.warning(
                "Host was probably closed before plugin was initialized."
            )
        elif result.lower() == "forbidden":
            log.warning("User didn't confirm saving files.")

    def _client(self):
        if not self.websocket_rpc:
            log.warning("Communicator's server did not start yet.")
            return None

        for client in self.websocket_rpc.clients:
            if not client.ws.closed:
                return client
        log.warning("Client is not yet connected to Communicator.")
        return None

    def client(self):
        if not self._connected_client or self._connected_client.ws.closed:
            self._connected_client = self._client()
        return self._connected_client

    def send_request(self, method, params=None):
        client = self.client()
        if not client:
            return

        return self.websocket_rpc.send_request(
            client, method, params
        )

    def send_notification(self, method, params=None):
        client = self.client()
        if not client:
            return

        self.websocket_rpc.send_notification(
            client, method, params
        )

    def execute_george(self, george_script):
        """Execute passed goerge script in TVPaint."""
        return self.send_request(
            "execute_george", [george_script]
        )

    def execute_george_through_file(self, george_script):
        """Execute george script with temp file.

        Allows to execute multiline george script without stopping websocket
        client.

        On windows make sure script does not contain paths with backwards
        slashes in paths, TVPaint won't execute properly in that case.

        Args:
            george_script (str): George script to execute. May be multilined.
        """
        temporary_file = tempfile.NamedTemporaryFile(
            mode="w", prefix="a_tvp_", suffix=".grg", delete=False
        )
        temporary_file.write(george_script)
        temporary_file.close()
        temp_file_path = temporary_file.name.replace("\\", "/")
        self.execute_george("tv_runscript {}".format(temp_file_path))
        os.remove(temp_file_path)


class QtCommunicator(BaseCommunicator):
    menu_definitions = {
        "title": "OpenPype Tools",
        "menu_items": [
            {
                "callback": "workfiles_tool",
                "label": "Workfiles",
                "help": "Open workfiles tool"
            }, {
                "callback": "loader_tool",
                "label": "Load",
                "help": "Open loader tool"
            }, {
                "callback": "creator_tool",
                "label": "Create",
                "help": "Open creator tool"
            }, {
                "callback": "scene_inventory_tool",
                "label": "Scene inventory",
                "help": "Open scene inventory tool"
            }, {
                "callback": "publish_tool",
                "label": "Publish",
                "help": "Open publisher"
            }, {
                "callback": "library_loader_tool",
                "label": "Library",
                "help": "Open library loader tool"
            }, {
                "callback": "subset_manager_tool",
                "label": "Subset Manager",
                "help": "Open subset manager tool"
            }, {
                "callback": "experimental_tools",
                "label": "Experimental tools",
                "help": "Open experimental tools dialog"
            }
        ]
    }

    def __init__(self, qt_app):
        super().__init__()
        self.callback_queue = Queue()
        self.qt_app = qt_app

    def _create_routes(self):
        self.websocket_rpc = QtTVPaintRpc(
            self, loop=self.websocket_server.loop
        )
        self.websocket_server.add_route(
            "*", "/", self.websocket_rpc.handle_request
        )

    def execute_in_main_thread(self, main_thread_item, wait=True):
        """Add `MainThreadItem` to callback queue and wait for result."""
        self.callback_queue.put(main_thread_item)
        if wait:
            return main_thread_item.wait()
        return

    async def async_execute_in_main_thread(self, main_thread_item, wait=True):
        """Add `MainThreadItem` to callback queue and wait for result."""
        self.callback_queue.put(main_thread_item)
        if wait:
            return await main_thread_item.async_wait()

    def main_thread_listen(self):
        """Get last `MainThreadItem` from queue.

        Must be called from main thread.

        Method checks if host process is still running as it may cause
        issues if not.
        """
        # check if host still running
        if self.process.poll() is not None:
            self._exit()
            return None

        if self.callback_queue.empty():
            return None
        return self.callback_queue.get()

    def _on_client_connect(self):
        super()._on_client_connect()
        self._build_menu()

    def _build_menu(self):
        self.send_request(
            "define_menu", [self.menu_definitions]
        )

    def _exit(self, *args, **kwargs):
        super()._exit(*args, **kwargs)
        emit_event("application.exit")
        self.qt_app.exit(self.exit_code)
