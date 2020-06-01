import os
import socket
from Qt import QtCore

from socketserver import ThreadingMixIn
from http.server import HTTPServer
from .lib import RestApiFactory, Handler
from .base_class import route, register_statics
from pype.api import config, Logger

log = Logger().get_logger("RestApiServer")


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


class RestApiServer:
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
        os.environ["PYPE_STATICS_SERVER"] = "{}/res".format(
            os.environ["PYPE_REST_API_URL"]
        )

    def set_qaction(self, qaction, failed_icon):
        self.qaction = qaction
        self.failed_icon = failed_icon

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
    Be careful about crossreferencing to different Threads it is not allowed.
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

            with ThreadingSimpleServer(("", self.port), Handler) as httpd:
                while self.is_running:
                    httpd.handle_request()
        except Exception:
            log.warning(
                "Rest Api Server service has failed", exc_info=True
            )

        self.is_running = False
        self.module.thread_stopped()
