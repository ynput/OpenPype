import os
import socket
from pype import resources
from .. import PypeModule, ITrayService


class WebServerModule(PypeModule, ITrayService):
    name = "webserver"
    label = "WebServer"

    def initialize(self, module_settings):
        self.enabled = True
        self.server_manager = None

        self.port = self.find_free_port()

    def connect_with_modules(self, *_a, **_kw):
        return

    def tray_init(self):
        self.create_server_manager()
        self._add_resources_statics()

    def tray_start(self):
        self.start_server()

    def tray_exit(self):
        self.stop_server()

    def _add_resources_statics(self):
        static_prefix = "/res"
        self.server_manager.add_static(static_prefix, resources.RESOURCES_DIR)

        os.environ["PYPE_STATICS_SERVER"] = "http://localhost:{}{}".format(
            self.port, static_prefix
        )

    def start_server(self):
        if self.server_manager:
            self.server_manager.start_server()

    def stop_server(self):
        if self.server_manager:
            self.server_manager.stop_server()

    def create_server_manager(self):
        if self.server_manager:
            return

        from .server import WebServerManager

        self.server_manager = WebServerManager(self)
        self.server_manager.on_stop_callbacks.append(
            self.set_service_failed_icon
        )

    @staticmethod
    def find_free_port(
        port_from=None, port_to=None, exclude_ports=None, host=None
    ):
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
        if port_from is None:
            port_from = 8079

        if port_to is None:
            port_to = 65535

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
