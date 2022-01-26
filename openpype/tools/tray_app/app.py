import os
import sys
import re
import collections
import queue
import websocket
import json
from datetime import datetime

from avalon import style
from openpype_modules.webserver import host_console_listener
from openpype.api import Logger

from Qt import QtWidgets, QtCore

log = Logger.get_logger(__name__)

class ConsoleTrayApp:
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

    def __init__(self, host, launch_method, subprocess_args, is_host_connected,
                 parent=None):
        self.host = host
        self.websocket_server = None
        self.launch_method = launch_method
        self.subprocess_args = subprocess_args
        self.is_host_connected = is_host_connected
        self.process = None

        self.original_stdout_write = None
        self.original_stderr_write = None
        self.new_text = collections.deque()

        start_process_timer = QtCore.QTimer()
        start_process_timer.setInterval(200)
        start_process_timer.timeout.connect(self._on_start_process_timer)
        start_process_timer.start()

        self.start_process_timer = start_process_timer

        loop_timer = QtCore.QTimer()
        loop_timer.setInterval(200)
        self.loop_timer = loop_timer

        start_process_timer.timeout.connect(self._on_start_process_timer)
        loop_timer.timeout.connect(self._on_loop_timer)

        self.catch_std_outputs()
        date_str = datetime.now().strftime("%d%m%Y%H%M%S")
        self.host_id = "{}_{}".format(self.host, date_str)

    @classmethod
    def instance(cls):
        if not cls._instance:
            raise RuntimeError("Not initialized yet")
        return cls._instance

    @property
    def websocket_server_is_running(self):
        if self.websocket_server is not None:
            return self.websocket_server.is_running
        return False

    @property
    def is_process_running(self):
        if self.process is not None:
            return self.process.poll() is None
        return False

    def _start_process(self):
        if self.process is not None:
            return
        log.info("Starting host process")
        try:
            self.launch_method(*self.subprocess_args)
        except Exception as exp:
            log.info("exce", exc_info=True)
            self.exit()

    def set_process(self, proc):
        if not self.process:
            self.process = proc

    def _connect_to_tray(self):
        """ Connect to Tray webserver to pass console output. """
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
            "action": host_console_listener.MsgAction.CONNECTING,
            "text": "Integration with {}".format(str.capitalize(self.host))
        }
        self._send(payload)

    def _disconnect_from_tray(self):
        """ Send to Tray that host is closing - remove from Services. """
        print("Host {} closing".format(self.host))
        if not self.webserver_client:
            return

        payload = {
            "host": self.host_id,
            "action": host_console_listener.MsgAction.CLOSE,
            "text": "Integration with {}".format(str.capitalize(self.host))
        }

        self._send(payload)
        self.webserver_client.close()

    def _host_connected(self):
        """ Send to Tray console that host is ready - icon change. """
        print("Host {} connected".format(self.host))
        self.start_process_timer.stop()
        self.loop_timer.start()

        self.callback_queue = queue.Queue()

        payload = {
            "host": self.host_id,
            "action": host_console_listener.MsgAction.INITIALIZED,
            "text": "Integration with {}".format(str.capitalize(self.host))
        }
        self._send(payload)

    def _send_text_queue(self):
        """Sends lines and purges queue"""
        lines = tuple(self.new_text)
        self.new_text.clear()

        if lines:
            self._send_lines(lines)

    def _send_lines(self, lines):
        """ Send console content. """
        if not self.webserver_client:
            return

        payload = {
            "host": self.host_id,
            "action": host_console_listener.MsgAction.ADD,
            "text": "\n".join(lines)
        }

        self._send(payload)

    def _send(self, payload):
        """ Worker method to send to existing websocket connection. """
        if not self.webserver_client:
            return

        try:
            self.webserver_client.send(json.dumps(payload))
        except ConnectionResetError:  # Tray closed
            self._connect_to_tray()

    def _on_start_process_timer(self):
        """Called periodically to initialize and run function on main thread"""
        if not self.webserver_client:
            self._connect_to_tray()

        self._send_text_queue()

        # Start application process
        if self.process is None:
            self._start_process()
            log.info("Waiting for host to connect")
            return

        host_connected = self.is_host_connected()
        if host_connected is None:  # keep trying
            return
        elif not host_connected:
            text = "{} process is not alive. Exiting".format(self.host)
            print(text)
            self._send_lines([text])
            self.exit()
        elif host_connected:
            self._host_connected()

    def _on_loop_timer(self):
        """Regular processing of queue"""
        if self.callback_queue and \
                not self.callback_queue.empty():
            try:
                callback = self.callback_queue.get(block=False)
                callback()
            except queue.Empty:
                pass
        elif self.process.poll() is not None:
            self.exit()

    def execute_in_main_thread(self, func_to_call_from_main_thread):
        """Put function to the queue to be picked by 'on_timer'"""
        if not self.callback_queue:
            self.callback_queue = queue.Queue()
        self.callback_queue.put(func_to_call_from_main_thread)

    def restart_server(self):
        if self.websocket_server:
            self.websocket_server.stop_server(restart=True)

    def exit(self):
        """ Exit whole application. """
        self._disconnect_from_tray()

        if self.websocket_server:
            self.websocket_server.stop()
        if self.process:
            self.process.kill()
            self.process.wait()
        if self.loop_timer:
            self.loop_timer.stop()
        QtCore.QCoreApplication.exit()

    def catch_std_outputs(self):
        """Redirects standard out and error to own functions"""
        # if not sys.stdout:
        #     dialog.append_text("Cannot read from stdout!")
        # else:
        #     self.original_stdout_write = sys.stdout.write
        #     sys.stdout.write = self.my_stdout_write
        #
        # if not sys.stderr:
        #     self.dialog.append_text("Cannot read from stderr!")
        # else:
        #     self.original_stderr_write = sys.stderr.write
        #     sys.stderr.write = self.my_stderr_write

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

        Find and replace all occurances of strings defined in dict is
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
