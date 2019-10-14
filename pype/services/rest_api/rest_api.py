import os
import re
import collections
import threading
import socket
import socketserver
from Qt import QtCore

from .lib import RestApiFactory, Handler
from .base_class import route, register_statics
from pypeapp import config, Logger

log = Logger().get_logger("RestApiServer")


class RestApiServer:
    def __init__(self):
        self.qaction = None
        self.failed_icon = None
        self._is_running = False

        try:
            self.presets = config.get_presets()["services"]["rest_api"]
        except Exception:
            self.presets = {"default_port": 8011, "exclude_ports": []}
            log.debug((
                "There are not set presets for RestApiModule."
                " Using defaults \"{}\""
            ).format(str(self.presets)))

        port = self.find_port()
        self.rest_api_thread = RestApiThread(self, port)

        statics_dir = os.path.sep.join([os.environ["PYPE_MODULE_ROOT"], "res"])
        self.register_statics("/res", statics_dir)

    def set_qaction(self, qaction, failed_icon):
        self.qaction = qaction
        self.failed_icon = failed_icon

    def register_callback(self, path, callback, url_prefix="", methods=[]):
        route(path, url_prefix, methods)(callback)

    def register_statics(self, url_prefix, dir_path):
        register_statics(url_prefix, dir_path)

    def register_obj(self, obj):
        RestApiFactory.register_obj(obj)

    def find_port(self):
        start_port = self.presets["default_port"]
        exclude_ports = self.presets["exclude_ports"]
        found_port = None
        # port check takes time so it's lowered to 100 ports
        for port in range(start_port, start_port+100):
            if port in exclude_ports:
                continue
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                result = sock.connect_ex(("localhost", port))
                if result != 0:
                    found_port = port
            if found_port is not None:
                break
        if found_port is None:
            return None
        os.environ["PYPE_REST_API_URL"] = "http://localhost:{}".format(
            found_port
        )
        return found_port

    def tray_start(self):
        RestApiFactory.prepare_registered()
        if not RestApiFactory.has_handlers():
            log.debug("There are not registered any handlers for RestApi")
            return
        self.rest_api_thread.start()

    @property
    def is_running(self):
        return self.rest_api_thread.is_running

    def stop(self):
        self.rest_api_thread.is_running = False

    def thread_stopped(self):
        self._is_running = False


class RestApiThread(QtCore.QThread):
    """ Listener for REST requests.

    It is possible to register callbacks for url paths.
    Be careful about crossreferencing to different QThreads it is not allowed.
    """

    def __init__(self, module, port):
        super(RestApiThread, self).__init__()
        self.is_running = False
        self.module = module
        self.port = port

    def run(self):
        self.is_running = True

        try:
            log.debug(
                "Running Rest Api server on URL:"
                " \"http://localhost:{}\"".format(self.port)
            )
            with socketserver.TCPServer(("", self.port), Handler) as httpd:
                while self.is_running:
                    httpd.handle_request()
        except Exception:
            log.warning(
                "Rest Api Server service has failed", exc_info=True
            )

        self.is_running = False
        self.module.thread_stopped()
