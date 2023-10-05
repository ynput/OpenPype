import os
import sys
import subprocess
import collections
import logging
import asyncio
import functools
import traceback


from wsrpc_aiohttp import (
    WebSocketRoute,
    WebSocketAsync
)

from qtpy import QtCore

from openpype.lib import Logger
from openpype.tests.lib import is_in_tests
from openpype.pipeline import install_host, legacy_io
from openpype.modules import ModulesManager
from openpype.tools.utils import host_tools, get_openpype_qt_app
from openpype.tools.adobe_webserver.app import WebServerTool

from .ws_stub import get_stub
from .lib import set_settings

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def safe_excepthook(*args):
    traceback.print_exception(*args)


def main(*subprocess_args):
    """Main entrypoint to AE launching, called from pre hook."""
    sys.excepthook = safe_excepthook

    from openpype.hosts.aftereffects.api import AfterEffectsHost

    host = AfterEffectsHost()
    install_host(host)

    os.environ["OPENPYPE_LOG_NO_COLORS"] = "False"
    app = get_openpype_qt_app()
    app.setQuitOnLastWindowClosed(False)

    launcher = ProcessLauncher(subprocess_args)
    launcher.start()

    if os.environ.get("HEADLESS_PUBLISH"):
        manager = ModulesManager()
        webpublisher_addon = manager["webpublisher"]

        launcher.execute_in_main_thread(
            functools.partial(
                webpublisher_addon.headless_publish,
                log,
                "CloseAE",
                is_in_tests()
            )
        )

    elif os.environ.get("AVALON_PHOTOSHOP_WORKFILES_ON_LAUNCH", True):
        save = False
        if os.getenv("WORKFILES_SAVE_AS"):
            save = True

        launcher.execute_in_main_thread(
            lambda: host_tools.show_tool_by_name("workfiles", save=save)
        )

    sys.exit(app.exec_())


def show_tool_by_name(tool_name):
    kwargs = {}
    if tool_name == "loader":
        kwargs["use_context"] = True

    host_tools.show_tool_by_name(tool_name, **kwargs)


class ProcessLauncher(QtCore.QObject):
    """Launches webserver, connects to it, runs main thread."""
    route_name = "AfterEffects"
    _main_thread_callbacks = collections.deque()

    def __init__(self, subprocess_args):
        self._subprocess_args = subprocess_args
        self._log = None

        super(ProcessLauncher, self).__init__()

        # Keep track if launcher was alreadu started
        self._started = False

        self._process = None
        self._websocket_server = None

        start_process_timer = QtCore.QTimer()
        start_process_timer.setInterval(100)

        loop_timer = QtCore.QTimer()
        loop_timer.setInterval(200)

        start_process_timer.timeout.connect(self._on_start_process_timer)
        loop_timer.timeout.connect(self._on_loop_timer)

        self._start_process_timer = start_process_timer
        self._loop_timer = loop_timer

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger("{}-launcher".format(
                self.route_name))
        return self._log

    @property
    def websocket_server_is_running(self):
        if self._websocket_server is not None:
            return self._websocket_server.is_running
        return False

    @property
    def is_process_running(self):
        if self._process is not None:
            return self._process.poll() is None
        return False

    @property
    def is_host_connected(self):
        """Returns True if connected, False if app is not running at all."""
        if not self.is_process_running:
            return False

        try:

            _stub = get_stub()
            if _stub:
                return True
        except Exception:
            pass

        return None

    @classmethod
    def execute_in_main_thread(cls, callback):
        cls._main_thread_callbacks.append(callback)

    def start(self):
        if self._started:
            return
        self.log.info("Started launch logic of AfterEffects")
        self._started = True
        self._start_process_timer.start()

    def exit(self):
        """ Exit whole application. """
        if self._start_process_timer.isActive():
            self._start_process_timer.stop()
        if self._loop_timer.isActive():
            self._loop_timer.stop()

        if self._websocket_server is not None:
            self._websocket_server.stop()

        if self._process:
            self._process.kill()
            self._process.wait()

        QtCore.QCoreApplication.exit()

    def _on_loop_timer(self):
        # TODO find better way and catch errors
        # Run only callbacks that are in queue at the moment
        cls = self.__class__
        for _ in range(len(cls._main_thread_callbacks)):
            if cls._main_thread_callbacks:
                callback = cls._main_thread_callbacks.popleft()
                callback()

        if not self.is_process_running:
            self.log.info("Host process is not running. Closing")
            self.exit()

        elif not self.websocket_server_is_running:
            self.log.info("Websocket server is not running. Closing")
            self.exit()

    def _on_start_process_timer(self):
        # TODO add try except validations for each part in this method
        # Start server as first thing
        if self._websocket_server is None:
            self._init_server()
            return

        # TODO add waiting time
        # Wait for webserver
        if not self.websocket_server_is_running:
            return

        # Start application process
        if self._process is None:
            self._start_process()
            self.log.info("Waiting for host to connect")
            return

        # TODO add waiting time
        # Wait until host is connected
        if self.is_host_connected:
            self._start_process_timer.stop()
            self._loop_timer.start()
        elif (
            not self.is_process_running
            or not self.websocket_server_is_running
        ):
            self.exit()

    def _init_server(self):
        if self._websocket_server is not None:
            return

        self.log.debug(
            "Initialization of websocket server for host communication"
        )

        self._websocket_server = websocket_server = WebServerTool()
        if websocket_server.port_occupied(
            websocket_server.host_name,
            websocket_server.port
        ):
            self.log.info(
                "Server already running, sending actual context and exit."
            )
            asyncio.run(websocket_server.send_context_change(self.route_name))
            self.exit()
            return

        # Add Websocket route
        websocket_server.add_route("*", "/ws/", WebSocketAsync)
        # Add after effects route to websocket handler

        print("Adding {} route".format(self.route_name))
        WebSocketAsync.add_route(
            self.route_name, AfterEffectsRoute
        )
        self.log.info("Starting websocket server for host communication")
        websocket_server.start_server()

    def _start_process(self):
        if self._process is not None:
            return
        self.log.info("Starting host process")
        try:
            self._process = subprocess.Popen(
                self._subprocess_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            self.log.info("exce", exc_info=True)
            self.exit()


class AfterEffectsRoute(WebSocketRoute):
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
        log.debug("someone called AfterEffects route")
        self.instance = self
        return kwargs

    # server functions
    async def ping(self):
        log.debug("someone called AfterEffects route ping")

    # This method calls function on the client side
    # client functions
    async def set_context(self, project, asset, task):
        """
            Sets 'project' and 'asset' to envs, eg. setting context

            Args:
                project (str)
                asset (str)
        """
        log.info("Setting context change")
        log.info("project {} asset {} ".format(project, asset))
        if project:
            legacy_io.Session["AVALON_PROJECT"] = project
            os.environ["AVALON_PROJECT"] = project
        if asset:
            legacy_io.Session["AVALON_ASSET"] = asset
            os.environ["AVALON_ASSET"] = asset
        if task:
            legacy_io.Session["AVALON_TASK"] = task
            os.environ["AVALON_TASK"] = task

    async def read(self):
        log.debug("aftereffects.read client calls server server calls "
                  "aftereffects client")
        return await self.socket.call('aftereffects.read')

    # panel routes for tools
    async def workfiles_route(self):
        self._tool_route("workfiles")

    async def loader_route(self):
        self._tool_route("loader")

    async def publish_route(self):
        self._tool_route("publisher")

    async def sceneinventory_route(self):
        self._tool_route("sceneinventory")

    async def setresolution_route(self):
        self._settings_route(False, True)

    async def setframes_route(self):
        self._settings_route(True, False)

    async def setall_route(self):
        self._settings_route(True, True)

    async def experimental_tools_route(self):
        self._tool_route("experimental_tools")

    def _tool_route(self, _tool_name):
        """The address accessed when clicking on the buttons."""

        partial_method = functools.partial(show_tool_by_name,
                                           _tool_name)

        ProcessLauncher.execute_in_main_thread(partial_method)

        # Required return statement.
        return "nothing"

    def _settings_route(self, frames, resolution):
        partial_method = functools.partial(set_settings,
                                           frames,
                                           resolution)

        ProcessLauncher.execute_in_main_thread(partial_method)

        # Required return statement.
        return "nothing"

    def create_placeholder_route(self):
        from openpype.hosts.aftereffects.api.workfile_template_builder import \
            create_placeholder
        partial_method = functools.partial(create_placeholder)

        ProcessLauncher.execute_in_main_thread(partial_method)

        # Required return statement.
        return "nothing"

    def update_placeholder_route(self):
        from openpype.hosts.aftereffects.api.workfile_template_builder import \
            update_placeholder
        partial_method = functools.partial(update_placeholder)

        ProcessLauncher.execute_in_main_thread(partial_method)

        # Required return statement.
        return "nothing"

    def build_workfile_template_route(self):
        from openpype.hosts.aftereffects.api.workfile_template_builder import \
            build_workfile_template
        partial_method = functools.partial(build_workfile_template)

        ProcessLauncher.execute_in_main_thread(partial_method)

        # Required return statement.
        return "nothing"

    def build_workfile_sequence_template_route(self):
        # from openpype.hosts.aftereffects.api.workfile_template_builder import \
        #     build_workfile_sequence_template
        # partial_method = functools.partial(build_workfile_sequence_template)

        # ProcessLauncher.execute_in_main_thread(partial_method)

        from importlib import reload
        from openpype.hosts.aftereffects.api import workfile_template_builder
        workfile_template_builder = reload(workfile_template_builder)

        partial_method = functools.partial(workfile_template_builder.
                                           build_workfile_sequence_template)
        ProcessLauncher.execute_in_main_thread(partial_method)

        # Required return statement.
        return "nothing"

    # def publish_multishot_route(self):
    #     from openpype.hosts.aftereffects.api.workfile_template_builder import \
    #         build_workfile_sequence_template
    #     partial_method = functools.partial(build_workfile_sequence_template)

    #     ProcessLauncher.execute_in_main_thread(partial_method)

    #     # Required return statement.
    #     return "nothing"
