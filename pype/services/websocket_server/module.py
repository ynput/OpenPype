import os
import socket
import threading
from .server import PypeWebsocketServer
from pypeapp import config, Logger


class WebSocketModule:
    def __init__(self):
        self.log = Logger().get_logger("RestApiServer")

        try:
            self.presets = config.get_presets()["services"]["websocket_server"]
        except Exception:
            self.presets = {"default_port": 8111, "exclude_ports": []}
            self.log.warning((
                "There are not set presets for WebSocketModule."
                " Using defaults \"{}\""
            ).format(str(self.presets)))

        port = self.find_port()
        self.server_thread = WebSocketThread(port)

    @property
    def server(self):
        return self.server_thread.server

    def find_port(self):
        start_port = self.presets["default_port"]
        exclude_ports = self.presets["exclude_ports"]
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
        os.environ["PYPE_WEBSOCKET_URL"] = "ws://localhost:{}".format(
            found_port
        )
        return found_port

    def register_namespace(self, namespace):
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


class WebSocketThread(threading.Thread):
    def __init__(self, port):
        self.server = PypeWebsocketServer(port)
        super(self.__class__, self).__init__()

    def run(self):
        self.server.start()

    def stop(self):
        self.server.stop()
