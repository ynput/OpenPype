import sys
import signal
import socket

from openpype_modules.ftrack.ftrack_server.ftrack_server import FtrackServer
from openpype_modules.ftrack.ftrack_server.lib import (
    SocketSession,
    SocketBaseEventHub
)
from openpype.modules import ModulesManager

from openpype.api import Logger

log = Logger().get_logger("FtrackUserServer")


def main(args):
    port = int(args[-1])

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    server_address = ("localhost", port)
    log.debug(
        "User Ftrack Server connected to {} port {}".format(*server_address)
    )
    sock.connect(server_address)
    sock.sendall(b"CreatedUser")

    try:
        session = SocketSession(
            auto_connect_event_hub=True, sock=sock, Eventhub=SocketBaseEventHub
        )
        manager = ModulesManager()
        ftrack_module = manager.modules_by_name["ftrack"]
        ftrack_module.user_event_handlers_paths
        server = FtrackServer(
            ftrack_module.user_event_handlers_paths
        )
        log.debug("Launching User Ftrack Server")
        server.run_server(session=session)

    except Exception:
        log.warning("Ftrack session server failed.", exc_info=True)

    finally:
        log.debug("Closing socket")
        sock.close()
        return 1


if __name__ == "__main__":
    Logger.set_process_name("Ftrack User server")

    # Register interupt signal
    def signal_handler(sig, frame):
        log.info(
            "Process was forced to stop. Process ended."
        )
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    sys.exit(main(sys.argv))
