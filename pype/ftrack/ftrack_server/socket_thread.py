import os
import sys
import time
import socket
import threading
import subprocess
from pypeapp import Logger


class SocketThread(threading.Thread):
    """Thread that checks suprocess of storer of processor of events"""

    MAX_TIMEOUT = 35

    def __init__(self, name, port, filepath):
        super(SocketThread, self).__init__()
        self.log = Logger().get_logger("SocketThread", "Event Thread")
        self.setName(name)
        self.name = name
        self.port = port
        self.filepath = filepath
        self.sock = None
        self.subproc = None
        self.connection = None
        self._is_running = False
        self.finished = False

        self.mongo_error = False

        self._temp_data = {}

    def stop(self):
        self._is_running = False

    def run(self):
        self._is_running = True
        time_socket = time.time()
        # Create a TCP/IP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock = sock

        # Bind the socket to the port - skip already used ports
        while True:
            try:
                server_address = ("localhost", self.port)
                sock.bind(server_address)
                break
            except OSError:
                self.port += 1

        self.log.debug(
            "Running Socked thread on {}:{}".format(*server_address)
        )

        self.subproc = subprocess.Popen(
            [sys.executable, self.filepath, "-port", str(self.port)]
        )

        # Listen for incoming connections
        sock.listen(1)
        sock.settimeout(1.0)
        while True:
            if not self._is_running:
                break
            try:
                connection, client_address = sock.accept()
                time_socket = time.time()
                connection.settimeout(1.0)
                self.connection = connection

            except socket.timeout:
                if (time.time() - time_socket) > self.MAX_TIMEOUT:
                    self.log.error("Connection timeout passed. Terminating.")
                    self._is_running = False
                    self.subproc.terminate()
                    break
                continue

            try:
                time_con = time.time()
                # Receive the data in small chunks and retransmit it
                while True:
                    try:
                        if not self._is_running:
                            break
                        data = None
                        try:
                            data = self.get_data_from_con(connection)
                            time_con = time.time()

                        except socket.timeout:
                            if (time.time() - time_con) > self.MAX_TIMEOUT:
                                self.log.error(
                                    "Connection timeout passed. Terminating."
                                )
                                self._is_running = False
                                self.subproc.terminate()
                                break
                            continue

                        except ConnectionResetError:
                            self._is_running = False
                            break

                        self._handle_data(connection, data)

                    except Exception as exc:
                        self.log.error(
                            "Event server process failed", exc_info=True
                        )

            finally:
                # Clean up the connection
                connection.close()
                if self.subproc.poll() is None:
                    self.subproc.terminate()

                self.finished = True

    def get_data_from_con(self, connection):
        return connection.recv(16)

    def _handle_data(self, connection, data):
        if not data:
            return

        if data == b"MongoError":
            self.mongo_error = True
        connection.sendall(data)
