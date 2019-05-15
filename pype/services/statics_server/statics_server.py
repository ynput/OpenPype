import os
import sys
import datetime
import socket
import http.server
from http import HTTPStatus
import urllib
import posixpath
import socketserver

from Qt import QtCore
from pypeapp import config, Logger


DIRECTORY = os.path.sep.join([os.environ['PYPE_MODULE_ROOT'], 'res'])


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        py_version = sys.version.split('.')
        # If python version is 3.7 or higher
        if int(py_version[0]) >= 3 and int(py_version[1]) >= 7:
            super().__init__(*args, directory=DIRECTORY, **kwargs)
        else:
            self.directory = DIRECTORY
            super().__init__(*args, **kwargs)

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            fs = os.fstat(f.fileno())
            # Use browser cache if possible
            if ("If-Modified-Since" in self.headers
                    and "If-None-Match" not in self.headers):
                # compare If-Modified-Since and time of last file modification
                try:
                    ims = http.server.email.utils.parsedate_to_datetime(
                        self.headers["If-Modified-Since"])
                except (TypeError, IndexError, OverflowError, ValueError):
                    # ignore ill-formed values
                    pass
                else:
                    if ims.tzinfo is None:
                        # obsolete format with no timezone, cf.
                        # https://tools.ietf.org/html/rfc7231#section-7.1.1.1
                        ims = ims.replace(tzinfo=datetime.timezone.utc)
                    if ims.tzinfo is datetime.timezone.utc:
                        # compare to UTC datetime of last modification
                        last_modif = datetime.datetime.fromtimestamp(
                            fs.st_mtime, datetime.timezone.utc)
                        # remove microseconds, like in If-Modified-Since
                        last_modif = last_modif.replace(microsecond=0)

                        if last_modif <= ims:
                            self.send_response(HTTPStatus.NOT_MODIFIED)
                            self.end_headers()
                            f.close()
                            return None

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified",
                self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        # Don't forget explicit trailing slash when normalizing. Issue17324
        trailing_slash = path.rstrip().endswith('/')
        try:
            path = urllib.parse.unquote(path, errors='surrogatepass')
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        path = posixpath.normpath(path)
        words = path.split('/')
        words = filter(None, words)
        path = self.directory
        for word in words:
            if os.path.dirname(word) or word in (os.curdir, os.pardir):
                # Ignore components that are not a simple file/directory name
                continue
            path = os.path.join(path, word)
        if trailing_slash:
            path += '/'
        return path


class StaticsServer(QtCore.QThread):
    """ Measure user's idle time in seconds.
    Idle time resets on keyboard/mouse input.
    Is able to emit signals at specific time idle.
    """
    def __init__(self):
        super(StaticsServer, self).__init__()
        self.qaction = None
        self.failed_icon = None
        self._is_running = False
        self.log = Logger().get_logger(self.__class__.__name__)
        try:
            self.presets = config.get_presets().get(
                'services', {}).get('statics_server')
        except Exception:
            self.presets = {'default_port': 8010, 'exclude_ports': []}

        self.port = self.find_port()

    def set_qaction(self, qaction, failed_icon):
        self.qaction = qaction
        self.failed_icon = failed_icon

    def tray_start(self):
        self.start()

    @property
    def is_running(self):
        return self._is_running

    def stop(self):
        self._is_running = False

    def run(self):
        self._is_running = True
        try:
            with socketserver.TCPServer(("", self.port), Handler) as httpd:
                while self._is_running:
                    httpd.handle_request()
        except Exception:
            self.log.warning(
                'Statics Server service has failed', exc_info=True
            )
        self._is_running = False
        if self.qaction and self.failed_icon:
            self.qaction.setIcon(self.failed_icon)

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
