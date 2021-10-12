import sys
import signal
import time
import socket

from .server import WebServerManager


class SharedObjects:
    stopped = False

    @classmethod
    def stop(cls):
        cls.stopped = True


def main(port=None, host=None):
    def signal_handler(sig, frame):
        print("Signal to kill process received. Termination starts.")
        SharedObjects.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    port = int(port or 8079)
    host = str(host or "localhost")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as con:
        result_of_check = con.connect_ex((host, port))

    if result_of_check == 0:
        print((
            "Server {}:{} is already running or address is occupied."
        ).format(host, port))
        return 1

    print("Running server {}:{}".format(host, port))
    manager = WebServerManager(port, host)
    manager.start_server()

    stopped = False
    while manager.is_running:
        if not stopped and SharedObjects.stopped:
            stopped = True
            manager.stop_server()
        time.sleep(0.1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
