import sys
import re
import platform
import collections
import queue
from io import StringIO

from avalon import style
from openpype import resources

from Qt import QtWidgets, QtGui, QtCore

class TrayApp(QtWidgets.QSystemTrayIcon):
    """Application showing console for non python hosts instead of cmd"""
    callback_queue = None

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

    def __init__(self, host, parent=None):
        super(TrayApp, self).__init__(parent)
        self.host = host

        self.initialized = False
        self.websocket_server = None
        self.timer = None
        self.subprocess_args = None
        self.initializing = False
        self.tray = False
        self.launch_method = None
        self.timer = None

        self.original_stdout_write = None
        self.original_stderr_write = None
        self.new_text = collections.deque()

        self.icons = self._select_icons(self.host)
        self.status_texts = self._prepare_status_texts(self.host)

        timer = QtCore.QTimer()
        timer.timeout.connect(self.on_timer)
        timer.setInterval(200)
        timer.start()

        self.timer = timer

        self.redirect_stds()

        menu = QtWidgets.QMenu()
        menu.setStyleSheet(style.load_stylesheet())
        # not working yet
        #
        # restart_server_action = QtWidgets.QAction("Restart communication",
        #                                           self)
        # restart_server_action.triggered.connect(self.restart_server)
        # menu.addAction(restart_server_action)

        # Add Exit action to menu
        exit_action = QtWidgets.QAction("Exit", self)
        exit_action.triggered.connect(self.exit)
        menu.addAction(exit_action)

        self.menu = menu

        self.dialog = ConsoleDialog(self.new_text)

        # Catch activate event for left click if not on MacOS
        #   - MacOS has this ability by design so menu would be doubled
        if platform.system().lower() != "darwin":
            self.activated.connect(self.on_systray_activated)

        self.change_status("initializing")
        self.setContextMenu(self.menu)
        self.show()

    def on_timer(self):
        """Called periodically to initialize and run function on main thread"""
        self.dialog.append_text(self.new_text)
        if not self.initialized:
            if self.initializing:
                return
            TrayApp.callback_queue = queue.Queue()
            self.initializing = True

            self.launch_method(*self.subprocess_args)
            self.initialized = True
            self.initializing = False
            self.change_status("ready")
        elif TrayApp.callback_queue:
            try:
                callback = TrayApp.callback_queue.get(block=False)
                callback()
            except queue.Empty:
                pass
        else:
            if self.process.poll() is not None:
                # Wait on Photoshop to close before closing the websocket serv.
                self.process.wait()
                self.websocket_server.stop()
                self.timer.stop()
                self.change_status("error")

    @classmethod
    def execute_in_main_thread(cls, func_to_call_from_main_thread):
        """Put function to the queue to be picked by 'on_timer'"""
        if not cls.callback_queue:
            cls.callback_queue = queue.Queue()
        cls.callback_queue.put(func_to_call_from_main_thread)

    def on_systray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Context:
            position = QtGui.QCursor().pos()
            self.menu.popup(position)
        else:
            self.open_console()

    @classmethod
    def restart_server(self):
        if TrayApp.websocket_server:
            TrayApp.websocket_server.stop_server(restart=True)

    def open_console(self):
        self.dialog.show()

    def exit(self):
        """ Exit whole application.

        - Icon won't stay in tray after exit.
        """
        TrayApp.process.kill()
        self.hide()
        QtCore.QCoreApplication.exit()

    def redirect_stds(self):
        """Redirects standard out and error to own functions"""
        if sys.stdout:
            self.original_stdout_write = sys.stdout.write
        else:
            sys.stdout = StringIO()

        if sys.stderr:
            self.original_stderr_write = sys.stderr.write
        else:
            sys.stderr = StringIO()

        sys.stdout.write = self.my_stdout_write
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

    def _prepare_status_texts(self, host_name):
        """Status text used as a tooltip"""
        status_texts = {
            'initializing': "Starting communication with {}".format(host_name),
            'ready': "Communicating with {}".format(host_name),
            'error': "Error!"
        }

        return status_texts

    def _select_icons(self, host_name):
        """Use different icons per state and host_name"""
        # use host_name
        icons = {
            'initializing': QtGui.QIcon(
                resources.get_resource("icons", "circle_orange.png")
            ),
            'ready': QtGui.QIcon(
                resources.get_resource("icons", "circle_green.png")
            ),
            'error': QtGui.QIcon(
                resources.get_resource("icons", "circle_red.png")
            )
        }

        return icons


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
        message = TrayApp._multiple_replace(message, TrayApp.sdict)

        return message

    def change_status(self, status):
        """Updates tooltip and icon with new status"""
        self._change_tooltip(status)
        self._change_icon(status)

    def _change_tooltip(self, status):
        status = self.status_texts.get(status)
        if not status:
            raise ValueError("Unknown state")

        self.setToolTip(status)

    def _change_icon(self, state):
        icon = self.icons.get(state)
        if not icon:
            raise ValueError("Unknown state")

        self.setIcon(icon)


class ConsoleDialog(QtWidgets.QDialog):
    """Qt dialog to show stdout instead of unwieldy cmd window"""
    WIDTH = 720
    HEIGHT = 450

    def __init__(self, text, parent=None):
        super(ConsoleDialog, self).__init__(parent)
        layout = QtWidgets.QHBoxLayout(parent)

        plain_text = QtWidgets.QPlainTextEdit(self)
        plain_text.setReadOnly(True)
        plain_text.resize(self.WIDTH, self.HEIGHT)
        while text:
            plain_text.appendPlainText(text.popleft().strip())

        layout.addWidget(plain_text)

        self.setWindowTitle("Console output")

        self.plain_text = plain_text

        self.setStyleSheet(style.load_stylesheet())

        self.resize(self.WIDTH, self.HEIGHT)

    def append_text(self, new_text):
        while new_text:
            self.plain_text.appendHtml(
                TrayApp.color(new_text.popleft().strip()))
