import sys
import signal
import socket

from ftrack_server import FtrackServer
from pype.ftrack.ftrack_server.lib import SocketSession, ProcessEventHub
from pypeapp import Logger

log = Logger().get_logger("Event processor")


def main(args):
    port = int(args[-1])
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    server_address = ("localhost", port)
    log.debug("Processor connected to {} port {}".format(*server_address))
    sock.connect(server_address)

    sock.sendall(b"CreatedProcess")
    try:
        session = SocketSession(
            auto_connect_event_hub=True, sock=sock, Eventhub=ProcessEventHub
        )
        server = FtrackServer("event")
        log.debug("Launched Ftrack Event processor")
        server.run_server(session)

    except Exception:
        log.error("Event server crashed. See traceback below", exc_info=True)

    finally:
        log.debug("First closing socket")
        sock.close()
        return 1


if __name__ == "__main__":
    # Register interupt signal
    def signal_handler(sig, frame):
        print("You pressed Ctrl+C. Process ended.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    sys.exit(main(sys.argv))
