import os
import json
import enum
import collections
import threading
from inspect import signature
import socket
import http.server
from http import HTTPStatus
import socketserver

from Qt import QtCore

from pypeapp import config, Logger

log = Logger().get_logger("RestApiServer")


class RestMethods(enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"

    def __repr__(self):
        return str(self.value)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return self == other

    def __hash__(self):
        return enum.Enum.__hash__(self)

    def __str__(self):
        return str(self.value)


class Handler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        self.process_request(RestMethods.GET)

    def do_POST(self):
        """Common code for POST.

        This trigger callbacks on specific paths.

        If request contain data and callback func has arg data are sent to
        callback too.

        Send back return values of callbacks.
        """
        self.process_request(RestMethods.POST)

    def process_request(self, rest_method):
        """Because processing is technically the same for now so it is used
        the same way
        """
        in_data = None
        cont_len = self.headers.get("Content-Length")
        if cont_len:
            content_length = int(cont_len)
            in_data_str = self.rfile.read(content_length)
            if in_data_str:
                in_data = json.loads(in_data_str)

        registered_callbacks = self.server.registered_callbacks[rest_method]

        path_items = [part.lower() for part in self.path.split("/") if part]
        request_path = "/".join(path_items)
        callback = registered_callbacks.get(request_path)
        result = None
        if callback:
            log.debug(
                "Triggering callbacks for path \"{}\"".format(request_path)
            )
            try:
                params = signature(callback).parameters
                if len(params) > 0 and in_data:
                    result = callback(in_data)
                else:
                    result = callback()

                self.send_response(HTTPStatus.OK)

                if result in [None, True] or isinstance(result, (str, int)):
                    message = str(result)
                    if result in [None, True]:
                        message = "{} request for \"{}\" passed".format(
                            rest_method, self.path
                        )

                    self.handle_result(rest_method, message=message)

                    return

                if isinstance(result, (dict, list)):
                    message = json.dumps(result).encode()
                    self.handle_result(rest_method, final_output=message)

                    return

            except Exception:
                message = "{} request for \"{}\" failed".format(
                    rest_method, self.path
                )
                log.error(message, exc_info=True)

                self.send_response(HTTPStatus.BAD_REQUEST)
                self.handle_result(rest_method, message=message, success=False)

                return

            self.handle_result(rest_method)

        else:
            message = (
            "{} request for \"{}\" don't have registered callback"
            ).format(rest_method, self.path)
            log.debug(message)

            self.send_response(HTTPStatus.NOT_FOUND)
            self.handle_result(rest_method, message=message, success=False)

    def handle_result(
        self, rest_method, final_output=None, message=None, success=True,
        content_type="application/json"
    ):
        self.send_header("Content-type", content_type)
        if final_output:
            output = final_output
        else:
            if not message:
                output = json.dumps({
                    "success": False,
                    "message": (
                        "{} request for \"{}\" has unexpected result"
                    ).format(rest_method, self.path)
                }).encode()

            else:
                output = json.dumps({
                    "success": success, "message": message
                }).encode()


        if isinstance(output, str):
            self.send_header("Content-Length", len(output))

        self.end_headers()

        if output:
            self.wfile.write(output)


class AdditionalArgsTCPServer(socketserver.TCPServer):
    def __init__(self, registered_callbacks, *args, **kwargs):
        self.registered_callbacks = registered_callbacks
        super(AdditionalArgsTCPServer, self).__init__(*args, **kwargs)


class RestApiServer(QtCore.QThread):
    """ Listener for REST requests.

    It is possible to register callbacks for url paths.
    Be careful about crossreferencing to different QThreads it is not allowed.
    """

    def __init__(self):
        super(RestApiServer, self).__init__()
        self.registered_callbacks = {
            RestMethods.GET: collections.defaultdict(list),
            RestMethods.POST: collections.defaultdict(list),
            RestMethods.PUT: collections.defaultdict(list),
            RestMethods.PATCH: collections.defaultdict(list),
            RestMethods.DELETE: collections.defaultdict(list)
        }

        self.qaction = None
        self.failed_icon = None
        self._is_running = False
        try:
            self.presets = config.get_presets().get(
                "services", {}).get(
                "rest_api", {}
            )
        except Exception:
            self.presets = {"default_port": 8011, "exclude_ports": []}

        self.port = self.find_port()

    def set_qaction(self, qaction, failed_icon):
        self.qaction = qaction
        self.failed_icon = failed_icon

    def register_callback(self, path, callback, rest_method=RestMethods.POST):
        if isinstance(path, (list, set)):
            path = "/".join([part.lower() for part in path])
        elif isinstance(path, str):
            path = "/".join(
                [part.lower() for part in str(path).split("/") if part]
            )

        if isinstance(rest_method, str):
            rest_method = str(rest_method).upper()

        if path in self.registered_callbacks[rest_method]:
            log.error(
                "Path \"{}\" has already registered callback.".format(path)
            )
            return False

        log.debug(
            "Registering callback for path \"{}\"".format(path)
        )
        self.registered_callbacks[rest_method][path] = callback

        return True

    def tray_start(self):
        self.start()

    @property
    def is_running(self):
        return self._is_running

    def stop(self):
        self._is_running = False

    def run(self):
        self._is_running = True
        if not self.registered_callbacks:
            log.info("Any registered callbacks for Rest Api server.")
            return

        try:
            log.debug(
                "Running Rest Api server on URL:"
                " \"http://localhost:{}\"".format(self.port)
            )
            with AdditionalArgsTCPServer(
                self.registered_callbacks,
                ("", self.port),
                Handler
            ) as httpd:
                while self._is_running:
                    httpd.handle_request()
        except Exception:
            log.warning(
                "Rest Api Server service has failed", exc_info=True
            )
        self._is_running = False
        if self.qaction and self.failed_icon:
            self.qaction.setIcon(self.failed_icon)

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
