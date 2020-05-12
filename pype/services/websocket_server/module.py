import os
import socket
from .server import WebSocketThread
from pypeapp import config, Logger


class WebSocketModule:
    default_port = 8111

    def __init__(self):
        self.log = Logger().get_logger("RestApiServer")

        presets = (
            config.get_presets()
            .get("services", {})
            .get("websocket_server")
        ) or {}
        if not presets:
            self.log.warning((
                "There are not set presets for WebSocketModule."
                " Using default port \"{}\""
            ).format(str(self.default_port)))

        start_port = presets.get("default_port", self.default_port)
        exclude_ports = presets.get("exclude_ports") or []

        port = self.find_port(start_port, exclude_ports)
        self.server_thread = WebSocketThread(port)

    @property
    def server(self):
        return self.server_thread.server

    def find_port(self, start_port, exclude_ports):
        """Make sure that port set in presets is available.

        When port is found WebSocket url is stored to "PYPE_WEBSOCKET_URL"
        environment variable.
        """
        found_port = None
        # port check takes time so it's lowered to 100 ports
        for port in range(start_port, start_port + 100):
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
        # TODO maybe would bebetter to store url when server starts to get
        # 100% sure right port
        os.environ["PYPE_WEBSOCKET_URL"] = "ws://localhost:{}".format(
            found_port
        )
        return found_port

    def register_namespace(self, namespace):
        """Register namespace where websocket server may listen for clients.

        Args:
            namespace (Namespace): Created object of Namespace class or class
                inherited from Namespace. Must have defined unique endpoint
                path.
        """
        endpoint = namespace.endpoint
        if endpoint in self.server.namespaces:
            raise AssertionError(
                "Duplicated namespace registration \"{}\"".format(endpoint)
            )

        namespace.server = self.server
        self.server.namespaces[endpoint] = namespace

    def tray_start(self):
        self.server_thread.start()

    def tray_exit(self):
        self.server_thread.stop()
        self.server_thread.join()
