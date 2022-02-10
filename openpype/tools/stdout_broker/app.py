import os
import sys
import threading
import collections
import websocket
import json
from datetime import datetime

from openpype_modules.webserver.host_console_listener import MsgAction
from openpype.api import Logger

log = Logger.get_logger(__name__)


class StdOutBroker:
    """
    Application showing console in Services tray for non python hosts
    instead of cmd window.
    """
    MAX_LINES = 10000
    TIMER_TIMEOUT = 0.200

    def __init__(self, host_name):
        self.host_name = host_name
        self.webserver_client = None

        self.original_stdout_write = None
        self.original_stderr_write = None
        self.log_queue = collections.deque()

        date_str = datetime.now().strftime("%d%m%Y%H%M%S")
        self.host_id = "{}_{}".format(self.host_name, date_str)

        self._std_available = False
        self._is_running = False
        self._catch_std_outputs()

        self._timer = None

    @property
    def send_to_tray(self):
        """Checks if connected to tray and have access to logs."""
        return self.webserver_client and self._std_available

    def start(self):
        """Start app, create and start timer"""
        if not self._std_available or self._is_running:
            return
        self._is_running = True
        self._create_timer()
        self._connect_to_tray()

    def stop(self):
        """Disconnect from Tray, process last logs"""
        if not self._is_running:
            return
        self._is_running = False
        self._process_queue()
        self._disconnect_from_tray()

    def host_connected(self):
        """Send to Tray console that host is ready - icon change. """
        log.info("Host {} connected".format(self.host_id))

        payload = {
            "host": self.host_id,
            "action": MsgAction.INITIALIZED,
            "text": "Integration with {}".format(
                str.capitalize(self.host_name))
        }
        self._send(payload)

    def _create_timer(self):
        timer = threading.Timer(self.TIMER_TIMEOUT, self._timer_callback)
        timer.start()
        self._timer = timer

    def _timer_callback(self):
        if not self._is_running:
            return
        self._process_queue()
        self._create_timer()

    def _connect_to_tray(self):
        """Connect to Tray webserver to pass console output. """
        if not self._std_available:  # not content to log
            return
        ws = websocket.WebSocket()
        webserver_url = os.environ.get("OPENPYPE_WEBSERVER_URL")

        if not webserver_url:
            print("Unknown webserver url, cannot connect to pass log")
            return

        webserver_url = webserver_url.replace("http", "ws")
        ws.connect("{}/ws/host_listener".format(webserver_url))
        self.webserver_client = ws

        payload = {
            "host": self.host_id,
            "action": MsgAction.CONNECTING,
            "text": "Integration with {}".format(
                str.capitalize(self.host_name))
        }
        self._send(payload)

    def _disconnect_from_tray(self):
        """Send to Tray that host is closing - remove from Services. """
        print("Host {} closing".format(self.host_name))
        if not self.webserver_client:
            return

        payload = {
            "host": self.host_id,
            "action": MsgAction.CLOSE,
            "text": "Integration with {}".format(
                str.capitalize(self.host_name))
        }

        self._send(payload)
        self.webserver_client.close()

    def _catch_std_outputs(self):
        """Redirects standard out and error to own functions"""
        if sys.stdout:
            self.original_stdout_write = sys.stdout.write
            sys.stdout.write = self._my_stdout_write
            self._std_available = True

        if sys.stderr:
            self.original_stderr_write = sys.stderr.write
            sys.stderr.write = self._my_stderr_write
            self._std_available = True

    def _my_stdout_write(self, text):
        """Appends outputted text to queue, keep writing to original stdout"""
        if self.original_stdout_write is not None:
            self.original_stdout_write(text)
        if self.send_to_tray:
            self.log_queue.append(text)

    def _my_stderr_write(self, text):
        """Appends outputted text to queue, keep writing to original stderr"""
        if self.original_stderr_write is not None:
            self.original_stderr_write(text)
        if self.send_to_tray:
            self.log_queue.append(text)

    def _process_queue(self):
        """Sends lines and purges queue"""
        if not self.send_to_tray:
            return

        lines = tuple(self.log_queue)
        self.log_queue.clear()
        if lines:
            payload = {
                "host": self.host_id,
                "action": MsgAction.ADD,
                "text": "\n".join(lines)
            }

            self._send(payload)

    def _send(self, payload):
        """Worker method to send to existing websocket connection."""
        if not self.send_to_tray:
            return

        try:
            self.webserver_client.send(json.dumps(payload))
        except ConnectionResetError:  # Tray closed
            self._connect_to_tray()
