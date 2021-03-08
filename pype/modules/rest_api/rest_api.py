import os
import socket
import threading
from abc import ABCMeta, abstractmethod
from socketserver import ThreadingMixIn
from http.server import HTTPServer

import six

from pype.lib import PypeLogger
from pype import resources

from .lib import RestApiFactory, Handler
from .base_class import route, register_statics
from .. import PypeModule, ITrayService


@six.add_metaclass(ABCMeta)
class IRestApi:
    """Other modules interface to return paths to ftrack event handlers.

    Expected output is dictionary with "server" and "user" keys.
    """
    @abstractmethod
    def rest_api_initialization(self, rest_api_module):
        pass


class RestApiModule(PypeModule, ITrayService):
    """Rest Api allows to access statics or callbacks with http requests.

    To register statics use `register_statics`.

    To register callback use `register_callback` method or use `route` decorator.
    `route` decorator should be used with not-class functions, it is possible
    to use within class when inherits `RestApi` (defined in `base_class.py`)
    or created object, with used decorator, is registered with `register_obj`.

    .. code-block:: python
        @route("/username", url_prefix="/api", methods=["get"], strict_match=False)
        def get_username():
            return {"username": getpass.getuser()}

    In that case response to `localhost:{port}/api/username` will be status
    `200` with body including `{"data": {"username": getpass.getuser()}}`

    Callback may expect one argument which will be filled with request
    info. Data object has attributes: `request_data`, `query`,
    `fragment`, `params`, `method`, `handler`, `url_data`.
    request_data - Data from request body if there are any.
    query - query from url path (?identificator=name)
    fragment - fragment from url path (#reset_credentials)
    params - params from url path
    method - request method (GET, POST, PUT, etc.)
    handler - Handler object of HttpServer Handler
    url_data - dynamic url keys from registered path with their values

    Dynamic url keys may be set with path argument.
    .. code-block:: python
        from rest_api import route

        all_projects = {
            "Proj1": {"proj_data": []},
            "Proj2": {"proj_data": []},
        }

        @route("/projects/<project_name>", url_prefix="/api", methods=["get"], strict_match=False)
        def get_projects(request_info):
            project_name = request_info.url_data["project_name"]
            if not project_name:
                return all_projects
            return all_projects.get(project_name)

    This example should end with status 404 if project is not found. In that
    case is best to use `abort` method.

    .. code-block:: python
        from rest_api import abort

        @route("/projects/<project_name>", url_prefix="/api", methods=["get"], strict_match=False)
        def get_projects(request_info):
            project_name = request_info.url_data["project_name"]
            if not project_name:
                return all_projects

            project = all_projects.get(project_name)
            if not project:
                abort(404, "Project \"{}\".format(project_name) was not found")
            return project

    `strict_match` allows to handle not only specific entity but all entity types.
    E.g. "/projects/<project_name>" with set `strict_match` to False will handle also
    "/projects" or "/projects/" path. It is necessary to set `strict_match` to
    True when should handle only single entity.

    Callback may return many types. For more information read docstring of
    `_handle_callback_result` defined in handler.
    """
    label = "Rest API Service"
    name = "rest_api"

    def initialize(self, modules_settings):
        rest_api_settings = modules_settings[self.name]
        self.enabled = True
        self.default_port = rest_api_settings["default_port"]
        self.exclude_ports = rest_api_settings["exclude_ports"]

        self.rest_api_url = None
        self.rest_api_thread = None

    def register_callback(
        self, path, callback, url_prefix="", methods=[], strict_match=False
    ):
        RestApiFactory.register_route(
            path, callback, url_prefix, methods, strict_match
        )

    def register_statics(self, url_prefix, dir_path):
        register_statics(url_prefix, dir_path)

    def register_obj(self, obj):
        RestApiFactory.register_obj(obj)

    def connect_with_modules(self, enabled_modules):
        # Do not register restapi callbacks out of tray
        if self.tray_initialized:
            for module in enabled_modules:
                if not isinstance(module, IRestApi):
                    continue

                module.rest_api_initialization(self)

    @staticmethod
    def find_free_port(port_from, port_to=None, exclude_ports=None, host=None):
        """Find available socket port from entered range.

        It is also possible to only check if entered port is available.

        Args:
            port_from (int): Port number which is checked as first.
            port_to (int): Last port that is checked in sequence from entered
                `port_from`. Only `port_from` is checked if is not entered.
                Nothing is processed if is equeal to `port_from`!
            exclude_ports (list, tuple, set): List of ports that won't be
                checked form entered range.
            host (str): Host where will check for free ports. Set to
                "localhost" by default.
        """
        # Check only entered port if `port_to` is not defined
        if port_to is None:
            port_to = port_from

        # Excluded ports (e.g. reserved for other servers/clients)
        if exclude_ports is None:
            exclude_ports = []

        # Default host is localhost but it is possible to look for other hosts
        if host is None:
            host = "localhost"

        found_port = None
        for port in range(port_from, port_to + 1):
            if port in exclude_ports:
                continue

            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind((host, port))
                found_port = port

            except socket.error:
                continue

            finally:
                if sock:
                    sock.close()

            if found_port is not None:
                break

        return found_port

    def tray_init(self):
        port = self.find_free_port(
            self.default_port, self.default_port + 100, self.exclude_ports
        )
        self.rest_api_url = "http://localhost:{}".format(port)
        self.rest_api_thread = RestApiThread(self, port)
        self.register_statics("/res", resources.RESOURCES_DIR)

        # Set rest api environments
        os.environ["PYPE_REST_API_URL"] = self.rest_api_url

    def tray_start(self):
        RestApiFactory.prepare_registered()
        if not RestApiFactory.has_handlers():
            self.log.debug("There are not registered any handlers for RestApi")
            return
        self.rest_api_thread.start()

    @property
    def is_running(self):
        return self.rest_api_thread.is_running

    def tray_exit(self):
        self.stop()

    def stop(self):
        self.rest_api_thread.stop()
        self.rest_api_thread.join()


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


class RestApiThread(threading.Thread):
    """ Listener for REST requests.

    It is possible to register callbacks for url paths.
    Be careful about crossreferencing to different Threads it is not allowed.
    """

    def __init__(self, module, port):
        super(RestApiThread, self).__init__()
        self.is_running = False
        self.module = module
        self.port = port
        self.httpd = None
        self.log = PypeLogger().get_logger("RestApiThread")

    def stop(self):
        self.is_running = False
        if self.httpd:
            self.httpd.server_close()

    def run(self):
        self.is_running = True

        try:
            self.log.debug(
                "Running Rest Api server on URL:"
                " \"http://localhost:{}\"".format(self.port)
            )

            with ThreadingSimpleServer(("", self.port), Handler) as httpd:
                self.httpd = httpd
                while self.is_running:
                    httpd.handle_request()

        except Exception:
            self.log.warning(
                "Rest Api Server service has failed", exc_info=True
            )

        self.httpd = None
        self.is_running = False
