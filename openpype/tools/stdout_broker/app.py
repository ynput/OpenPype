import os
import sys
import re
import collections
import websocket
import json
from datetime import datetime

from avalon import style
from openpype_modules.webserver.host_console_listener import MsgAction

from openpype.api import Logger

from Qt import QtWidgets, QtCore

log = Logger.get_logger(__name__)


class StdOutBroker:
    """
    Application showing console in Services tray for non python hosts
    instead of cmd window.
    """
    callback_queue = None
    process = None
    webserver_client = None
    _instance = None

    MAX_LINES = 10000

    sdict = {
        r">>> ":
            '<span style="font-weight: bold;color:#EE5C42"> >>> </span>',
        r"!!!(?!\sCRI|\sERR)":
            '<span style="font-weight: bold;color:red"> !!! </span>',
        r"\-\-\- ":
            '<span style="font-weight: bold;color:cyan"> --- </span>',
        r"\*\*\*(?!\sWRN)":
            '<span style="font-weight: bold;color:#FFD700"> *** </span>',
        r"\*\*\* WRN":
            '<span style="font-weight: bold;color:#FFD700"> *** WRN</span>',
        r"  \- ":
            '<span style="font-weight: bold;color:#FFD700">  - </span>',
        r"\[ ":
            '<span style="font-weight: bold;color:#66CDAA">[</span>',
        r"\]":
            '<span style="font-weight: bold;color:#66CDAA">]</span>',
        r"{":
            '<span style="color:#66CDAA">{',
        r"}":
            r"}</span>",
        r"\(":
            '<span style="color:#66CDAA">(',
        r"\)":
            r")</span>",
        r"^\.\.\. ":
            '<span style="font-weight: bold;color:#EE5C42"> ... </span>',
        r"!!! ERR: ":
            '<span style="font-weight: bold;color:#EE5C42"> !!! ERR: </span>',
        r"!!! CRI: ":
            '<span style="font-weight: bold;color:red"> !!! CRI: </span>',
        r"(?i)failed":
            '<span style="font-weight: bold;color:#EE5C42"> FAILED </span>',
        r"(?i)error":
            '<span style="font-weight: bold;color:#EE5C42"> ERROR </span>'
    }

    def __init__(self, host_name):
        self.host_name = host_name
        self.websocket_server = None

        self.original_stdout_write = None
        self.original_stderr_write = None
        self.log_queue = collections.deque()

        date_str = datetime.now().strftime("%d%m%Y%H%M%S")
        self.host_id = "{}_{}".format(self.host_name, date_str)

        self._std_available = False
        self._catch_std_outputs()
        self._connect_to_tray()

        loop_timer = QtCore.QTimer()
        loop_timer.setInterval(200)
        loop_timer.timeout.connect(self._process_queue)
        self.loop_timer = loop_timer

    @property
    def websocket_server_is_running(self):
        if self.websocket_server is not None:
            return self.websocket_server.is_running
        return False

    @property
    def send_to_tray(self):
        """Checks if connected to tray and have access to logs."""
        return self.webserver_client and self._std_available

    def _connect_to_tray(self):
        """ Connect to Tray webserver to pass console output. """
        if not self._std_available: # not content to log
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
        """ Send to Tray that host is closing - remove from Services. """
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

    def host_connected(self):
        """ Send to Tray console that host is ready - icon change. """
        log.info("Host {} connected".format(self.host_id))

        payload = {
            "host": self.host_id,
            "action": MsgAction.INITIALIZED,
            "text": "Integration with {}".format(
                str.capitalize(self.host_name))
        }
        self._send(payload)
        self.loop_timer.start()

    def restart_server(self):
        if self.websocket_server:
            self.websocket_server.stop_server(restart=True)

    def exit(self):
        """ Exit whole application. """
        self._disconnect_from_tray()

        if self.websocket_server:
            self.websocket_server.stop()
        QtCore.QCoreApplication.exit()

    def _catch_std_outputs(self):
        """Redirects standard out and error to own functions"""
        if sys.stdout:
            self.original_stdout_write = sys.stdout.write
            sys.stdout.write = self.my_stdout_write
            self._std_available = True

        if sys.stderr:
            self.original_stderr_write = sys.stderr.write
            sys.stderr.write = self.my_stderr_write
            self._std_available = True

    def my_stdout_write(self, text):
        """Appends outputted text to queue, keep writing to original stdout"""
        if self.original_stdout_write is not None:
            self.original_stdout_write(text)
        if self.send_to_tray:
            self.log_queue.append(text)

    def my_stderr_write(self, text):
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
        """ Worker method to send to existing websocket connection."""
        if not self.send_to_tray:
            return

        try:
            self.webserver_client.send(json.dumps(payload))
        except ConnectionResetError:  # Tray closed
            self._connect_to_tray()

    @staticmethod
    def _multiple_replace(text, adict):
        """Replace multiple tokens defined in dict.

        Find and replace all occurrences of strings defined in dict is
        supplied string.

        Args:
            text (str): string to be searched
            adict (dict): dictionary with `{'search': 'replace'}`

        Returns:
            str: string with replaced tokens

        """
        for r, v in adict.items():
            text = re.sub(r, v, text)

        return text

    @staticmethod
    def color(message):
        """ Color message with html tags. """
        message = StdOutBroker._multiple_replace(message,
                                                 StdOutBroker.sdict)

        return message


class ConsoleDialog(QtWidgets.QDialog):
    """Qt dialog to show stdout instead of unwieldy cmd window"""
    WIDTH = 720
    HEIGHT = 450
    MAX_LINES = 10000

    def __init__(self, text, parent=None):
        super(ConsoleDialog, self).__init__(parent)
        layout = QtWidgets.QHBoxLayout(parent)

        plain_text = QtWidgets.QPlainTextEdit(self)
        plain_text.setReadOnly(True)
        plain_text.resize(self.WIDTH, self.HEIGHT)
        plain_text.maximumBlockCount = self.MAX_LINES

        while text:
            plain_text.appendPlainText(text.popleft().strip())

        layout.addWidget(plain_text)

        self.setWindowTitle("Console output")

        self.plain_text = plain_text

        self.setStyleSheet(style.load_stylesheet())

        self.resize(self.WIDTH, self.HEIGHT)

    def append_text(self, new_text):
        if isinstance(new_text, str):
            new_text = collections.deque(new_text.split("\n"))
        while new_text:
            text = new_text.popleft()
            if text:
                self.plain_text.appendHtml(StdOutBroker.color(text))
