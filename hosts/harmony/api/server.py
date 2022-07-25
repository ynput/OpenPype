# -*- coding: utf-8 -*-
"""Server-side implementation of Toon Boon Harmony communication."""
import socket
import logging
import json
import traceback
import importlib
import functools
import time
import struct
from datetime import datetime
import threading
from . import lib


class Server(threading.Thread):
    """Class for communication with Toon Boon Harmony.

    Attributes:
        connection (Socket): connection holding object.
        received (str): received data buffer.any(iterable)
        port (int): port number.
        message_id (int): index of last message going out.
        queue (dict): dictionary holding queue of incoming messages.

    """

    def __init__(self, port):
        """Constructor."""
        super(Server, self).__init__()
        self.daemon = True
        self.connection = None
        self.received = ""
        self.port = port
        self.message_id = 1

        # Setup logging.
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)

        # Create a TCP/IP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to the port
        server_address = ("127.0.0.1", port)
        self.log.debug(
            f"[{self.timestamp()}] Starting up on "
            f"{server_address[0]}:{server_address[1]}")
        self.socket.bind(server_address)

        # Listen for incoming connections
        self.socket.listen(1)
        self.queue = {}

    def process_request(self, request):
        """Process incoming request.

        Args:
            request (dict): {
                "module": (str),  # Module of method.
                "method" (str),  # Name of method in module.
                "args" (list),  # Arguments to pass to method.
                "kwargs" (dict),  # Keywork arguments to pass to method.
                "reply" (bool),  # Optional wait for method completion.
            }
        """
        pretty = self._pretty(request)
        self.log.debug(
            f"[{self.timestamp()}] Processing request:\n{pretty}")

        try:
            module = importlib.import_module(request["module"])
            method = getattr(module, request["method"])

            args = request.get("args", [])
            kwargs = request.get("kwargs", {})
            partial_method = functools.partial(method, *args, **kwargs)

            lib.ProcessContext.execute_in_main_thread(partial_method)
        except Exception:
            self.log.error(traceback.format_exc())

    def receive(self):
        """Receives data from `self.connection`.

        When the data is a json serializable string, a reply is sent then
        processing of the request.
        """
        current_time = time.time()
        while True:
            self.log.info("wait ttt")
            # Receive the data in small chunks and retransmit it
            request = None
            header = self.connection.recv(10)
            if len(header) == 0:
                # null data received, socket is closing.
                self.log.info(f"[{self.timestamp()}] Connection closing.")
                break

            if header[0:2] != b"AH":
                self.log.error("INVALID HEADER")
            content_length_str = header[2:].decode()

            length = int(content_length_str, 16)
            data = self.connection.recv(length)
            while (len(data) < length):
                # we didn't received everything in first try, lets wait for
                # all data.
                self.log.info("loop")
                time.sleep(0.1)
                if self.connection is None:
                    self.log.error(f"[{self.timestamp()}] "
                                   "Connection is broken")
                    break
                if time.time() > current_time + 30:
                    self.log.error(f"[{self.timestamp()}] Connection timeout.")
                    break

                data += self.connection.recv(length - len(data))
            self.log.debug("data:: {} {}".format(data, type(data)))
            self.received += data.decode("utf-8")
            pretty = self._pretty(self.received)
            self.log.debug(
                f"[{self.timestamp()}] Received:\n{pretty}")

            try:
                request = json.loads(self.received)
            except json.decoder.JSONDecodeError as e:
                self.log.error(f"[{self.timestamp()}] "
                               f"Invalid message received.\n{e}",
                               exc_info=True)

            self.received = ""
            if request is None:
                continue

            if "message_id" in request.keys():
                message_id = request["message_id"]
                self.message_id = message_id + 1
                self.log.debug(f"--- storing request as {message_id}")
                self.queue[message_id] = request
            if "reply" not in request.keys():
                request["reply"] = True
                self.send(request)
                self.process_request(request)

                if "message_id" in request.keys():
                    try:
                        self.log.debug(f"[{self.timestamp()}] "
                                       f"Removing from the queue {message_id}")
                        del self.queue[message_id]
                    except IndexError:
                        self.log.debug(f"[{self.timestamp()}] "
                                       f"{message_id} is no longer in queue")
            else:
                self.log.debug(f"[{self.timestamp()}] "
                               "received data was just a reply.")

    def run(self):
        """Entry method for server.

        Waits for a connection on `self.port` before going into listen mode.
        """
        # Wait for a connection
        timestamp = datetime.now().strftime("%H:%M:%S.%f")
        self.log.debug(f"[{timestamp}] Waiting for a connection.")
        self.connection, client_address = self.socket.accept()

        timestamp = datetime.now().strftime("%H:%M:%S.%f")
        self.log.debug(f"[{timestamp}] Connection from: {client_address}")

        self.receive()

    def stop(self):
        """Shutdown socket server gracefully."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")
        self.log.debug(f"[{timestamp}] Shutting down server.")
        if self.connection is None:
            self.log.debug("Connect to shutdown.")
            socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
            ).connect(("localhost", self.port))

        self.connection.close()
        self.connection = None

        self.socket.close()

    def _send(self, message):
        """Send a message to Harmony.

        Args:
            message (str): Data to send to Harmony.
        """
        # Wait for a connection.
        while not self.connection:
            pass

        timestamp = datetime.now().strftime("%H:%M:%S.%f")
        encoded = message.encode("utf-8")
        coded_message = b"AH" + struct.pack('>I', len(encoded)) + encoded
        pretty = self._pretty(coded_message)
        self.log.debug(
            f"[{timestamp}] Sending [{self.message_id}]:\n{pretty}")
        self.log.debug(f"--- Message length: {len(encoded)}")
        self.connection.sendall(coded_message)
        self.message_id += 1

    def send(self, request):
        """Send a request in dictionary to Harmony.

        Waits for a reply from Harmony.

        Args:
            request (dict): Data to send to Harmony.
        """
        request["message_id"] = self.message_id
        self._send(json.dumps(request))
        if request.get("reply"):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")
            self.log.debug(
                f"[{timestamp}] sent reply, not waiting for anything.")
            return None
        result = None
        current_time = time.time()
        try_index = 1
        while True:
            time.sleep(0.1)
            if time.time() > current_time + 30:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")
                self.log.error((f"[{timestamp}][{self.message_id}] "
                                "No reply from Harmony in 30s. "
                                f"Retrying {try_index}"))
                try_index += 1
                current_time = time.time()
            if try_index > 30:
                break
            try:
                result = self.queue[request["message_id"]]
                timestamp = datetime.now().strftime("%H:%M:%S.%f")
                self.log.debug((f"[{timestamp}] Got request "
                                f"id {self.message_id}, "
                                "removing from queue"))
                del self.queue[request["message_id"]]
                break
            except KeyError:
                # response not in received queue yey
                pass
            try:
                result = json.loads(self.received)
                break
            except json.decoder.JSONDecodeError:
                pass

        self.received = ""

        return result

    def _pretty(self, message) -> str:
        # result = pformat(message, indent=2)
        # return result.replace("\\n", "\n")
        return "{}{}".format(4 * " ", message)

    def timestamp(self):
        """Return current timestamp as a string.

        Returns:
            str: current timestamp.

        """
        return datetime.now().strftime("%H:%M:%S.%f")
