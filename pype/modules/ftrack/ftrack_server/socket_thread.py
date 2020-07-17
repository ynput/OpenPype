import os
import sys
import time
import socket
import threading
import traceback
import subprocess
from pype.api import Logger


class SocketThread(threading.Thread):
    """Thread that checks suprocess of storer of processor of events"""

    MAX_TIMEOUT = int(os.environ.get("PYPE_FTRACK_SOCKET_TIMEOUT", 45))

    def __init__(self, name, port, filepath, additional_args=[]):
        super(SocketThread, self).__init__()
        self.log = Logger().get_logger(self.__class__.__name__)
        self.setName(name)
        self.name = name
        self.port = port
        self.filepath = filepath
        self.additional_args = additional_args

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
            [
                sys.executable,
                self.filepath,
                *self.additional_args,
                str(self.port)
            ],
            stdin=subprocess.PIPE
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


class StatusSocketThread(SocketThread):
    process_name_mapping = {
        b"RestartS": "storer",
        b"RestartP": "processor",
        b"RestartM": "main"
    }

    def __init__(self, *args, **kwargs):
        self.process_threads = {}
        self.stop_subprocess = False
        super(StatusSocketThread, self).__init__(*args, **kwargs)

    def set_process(self, process_name, thread):
        try:
            if not self.subproc:
                self.process_threads[process_name] = None
                return

            if (
                process_name in self.process_threads and
                self.process_threads[process_name] == thread
            ):
                return

            self.process_threads[process_name] = thread
            self.subproc.stdin.write(
                str.encode("reset:{}\r\n".format(process_name))
            )
            self.subproc.stdin.flush()

        except Exception:
            print("Could not set thread in StatusSocketThread")
            traceback.print_exception(*sys.exc_info())

    def _handle_data(self, connection, data):
        if not data:
            return

        process_name = self.process_name_mapping.get(data)
        if process_name:
            if process_name == "main":
                self.stop_subprocess = True
            else:
                subp = self.process_threads.get(process_name)
                if subp:
                    subp.stop()
        connection.sendall(data)
