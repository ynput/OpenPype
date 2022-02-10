import os
import sys
import re
import collections
import queue
import websocket
import json
import itertools
from datetime import datetime

from avalon import style
from openpype_modules.webserver import host_console_listener

from Qt import QtWidgets, QtCore


class ConsoleTrayApp:
    """
    Application showing console in Services tray for non python hosts
    instead of cmd window.
    """
    callback_queue = None
    process = None
    webserver_client = None

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

    def __init__(self, host, launch_method, subprocess_args, is_host_connected,
                 parent=None):
        self.host = host

        self.initialized = False
        self.websocket_server = None
        self.initializing = False
        self.tray = False
        self.launch_method = launch_method
        self.subprocess_args = subprocess_args
        self.is_host_connected = is_host_connected
        self.tray_reconnect = True

        self.original_stdout_write = None
        self.original_stderr_write = None
        self.new_text = collections.deque()

        timer = QtCore.QTimer()
        timer.timeout.connect(self.on_timer)
        timer.setInterval(200)
        timer.start()

        self.timer = timer

        self.catch_std_outputs()
        date_str = datetime.now().strftime("%d%m%Y%H%M%S")
        self.host_id = "{}_{}".format(self.host, date_str)

    def _connect(self):
        """ Connect to Tray webserver to pass console output. """
        ws = websocket.WebSocket()
        webserver_url = os.environ.get("OPENPYPE_WEBSERVER_URL")

        if not webserver_url:
            print("Unknown webserver url, cannot connect to pass log")
            self.tray_reconnect = False
            return

        webserver_url = webserver_url.replace("http", "ws")
        ws.connect("{}/ws/host_listener".format(webserver_url))
        ConsoleTrayApp.webserver_client = ws

        payload = {
            "host": self.host_id,
            "action": host_console_listener.MsgAction.CONNECTING,
            "text": "Integration with {}".format(str.capitalize(self.host))
        }
        self.tray_reconnect = False
        self._send(payload)

    def _connected(self):
        """ Send to Tray console that host is ready - icon change. """
        print("Host {} connected".format(self.host))
        if not ConsoleTrayApp.webserver_client:
            return

        payload = {
            "host": self.host_id,
            "action": host_console_listener.MsgAction.INITIALIZED,
            "text": "Integration with {}".format(str.capitalize(self.host))
        }
        self.tray_reconnect = False
        self._send(payload)

    def _close(self):
        """ Send to Tray that host is closing - remove from Services. """
        print("Host {} closing".format(self.host))
        if not ConsoleTrayApp.webserver_client:
            return

        payload = {
            "host": self.host_id,
            "action": host_console_listener.MsgAction.CLOSE,
            "text": "Integration with {}".format(str.capitalize(self.host))
        }

        self._send(payload)
        self.tray_reconnect = False
        ConsoleTrayApp.webserver_client.close()

    def _send_text_queue(self):
        """Sends lines and purges queue"""
        lines = tuple(self.new_text)
        self.new_text.clear()

        if lines:
            self._send_lines(lines)

    def _send_lines(self, lines):
        """ Send console content. """
        if not ConsoleTrayApp.webserver_client:
            return

        payload = {
            "host": self.host_id,
            "action": host_console_listener.MsgAction.ADD,
            "text": "\n".join(lines)
        }

        self._send(payload)

    def _send(self, payload):
        """ Worker method to send to existing websocket connection. """
        if not ConsoleTrayApp.webserver_client:
            return

        try:
            ConsoleTrayApp.webserver_client.send(json.dumps(payload))
        except ConnectionResetError:  # Tray closed
            ConsoleTrayApp.webserver_client = None
            self.tray_reconnect = True

    def on_timer(self):
        """Called periodically to initialize and run function on main thread"""
        if self.tray_reconnect:
            self._connect()  # reconnect

        self._send_text_queue()

        if not self.initialized:
            if self.initializing:
                host_connected = self.is_host_connected()
                if host_connected is None:  # keep trying
                    return
                elif not host_connected:
                    text = "{} process is not alive. Exiting".format(self.host)
                    print(text)
                    self._send_lines([text])
                    ConsoleTrayApp.websocket_server.stop()
                    sys.exit(1)
                elif host_connected:
                    self.initialized = True
                    self.initializing = False
                    self._connected()

                    return

            ConsoleTrayApp.callback_queue = queue.Queue()
            self.initializing = True

            self.launch_method(*self.subprocess_args)
        elif ConsoleTrayApp.callback_queue and \
                not ConsoleTrayApp.callback_queue.empty():
            try:
                callback = ConsoleTrayApp.callback_queue.get(block=False)
                callback()
            except queue.Empty:
                pass
        elif ConsoleTrayApp.process.poll() is not None:
            self.exit()

    @classmethod
    def execute_in_main_thread(cls, func_to_call_from_main_thread):
        """Put function to the queue to be picked by 'on_timer'"""
        if not cls.callback_queue:
            cls.callback_queue = queue.Queue()
        cls.callback_queue.put(func_to_call_from_main_thread)

    @classmethod
    def restart_server(cls):
        if ConsoleTrayApp.websocket_server:
            ConsoleTrayApp.websocket_server.stop_server(restart=True)

    # obsolete
    def exit(self):
        """ Exit whole application. """
        self._close()
        if ConsoleTrayApp.websocket_server:
            ConsoleTrayApp.websocket_server.stop()
        if ConsoleTrayApp.process:
            ConsoleTrayApp.process.kill()
            ConsoleTrayApp.process.wait()
        if self.timer:
            self.timer.stop()
        QtCore.QCoreApplication.exit()

    def catch_std_outputs(self):
        """Redirects standard out and error to own functions"""
        if not sys.stdout:
            self.dialog.append_text("Cannot read from stdout!")
        else:
            self.original_stdout_write = sys.stdout.write
            sys.stdout.write = self.my_stdout_write

        if not sys.stderr:
            self.dialog.append_text("Cannot read from stderr!")
        else:
            self.original_stderr_write = sys.stderr.write
            sys.stderr.write = self.my_stderr_write

    def my_stdout_write(self, text):
        """Appends outputted text to queue, keep writing to original stdout"""
        if self.original_stdout_write is not None:
            self.original_stdout_write(text)
        self.new_text.append(text)

    def my_stderr_write(self, text):
        """Appends outputted text to queue, keep writing to original stderr"""
        if self.original_stderr_write is not None:
            self.original_stderr_write(text)
        self.new_text.append(text)

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
        message = ConsoleTrayApp._multiple_replace(message,
                                                   ConsoleTrayApp.sdict)

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
                self.plain_text.appendHtml(
                    ConsoleTrayApp.color(text))
