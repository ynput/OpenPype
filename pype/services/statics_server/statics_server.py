import os
import socket
import http.server
import socketserver

from Qt import QtCore
from pypeapp import config, Logger


DIRECTORY = os.path.sep.join([os.environ['PYPE_MODULE_ROOT'], 'res'])


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)


class StaticsServer(QtCore.QThread):
    """ Measure user's idle time in seconds.
    Idle time resets on keyboard/mouse input.
    Is able to emit signals at specific time idle.
    """

    def __init__(self):
        super(StaticsServer, self).__init__()
        self._is_running = False
        self._failed = False
        self.log = Logger().get_logger(self.__class__.__name__)
        try:
            self.presets = config.get_presets().get(
                'services', {}).get('statics_server')
        except Exception:
            self.presets = {'default_port': 8010, 'exclude_ports': []}

        self.port = self.find_port()

    def tray_start(self):
        self.start()

    @property
    def is_running(self):
        return self._is_running

    @property
    def failed(self):
        return self._failed

    def stop(self):
        self._is_running = False

    def run(self):
        self._is_running = True
        try:
            with socketserver.TCPServer(("", self.port), Handler) as httpd:
                while self._is_running:
                    httpd.handle_request()
        except Exception:
            self._failed = True
            self._is_running = False

    def find_port(self):
        start_port = self.presets['default_port']
        exclude_ports = self.presets['exclude_ports']
        found_port = None
        # port check takes time so it's lowered to 100 ports
        for port in range(start_port, start_port+100):
            if port in exclude_ports:
                continue
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                result = sock.connect_ex(('localhost', port))
                if result != 0:
                    found_port = port
            if found_port is not None:
                break
        if found_port is None:
            return None
        os.environ['PYPE_STATICS_SERVER'] = 'http://localhost:{}'.format(found_port)
        return found_port
