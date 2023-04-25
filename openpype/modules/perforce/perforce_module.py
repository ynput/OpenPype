from openpype.modules import OpenPypeModule, ITrayService
import socket

from openpype.modules.perforce.server import P4ServerManager


class PerforceModule(OpenPypeModule, ITrayService):
    name = "perforce"
    label = "Perforce"

    def initialize(self, module_settings):
        self.enabled = module_settings[self.name]["enabled"]
        self.server_manager = None
        self.server = None
        self.port = self.find_free_port(port_from=10000)

    def tray_init(self):


        self.server_manager = P4ServerManager(self.port, "0.0.0.0")


    def tray_start(self):
        self.start_server()

    def tray_exit(self):
        self.stop_server()

    def start_server(self):
        if self.server_manager:
            self.server_manager.start_server()

    def stop_server(self):
        if self.server_manager:
            self.server_manager.stop_server()

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
                Nothing is processed if is equal to `port_from`!
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
