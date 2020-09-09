"""
Logging to console and to mongo. For mongo logging, you need to set either
``PYPE_LOG_MONGO_URL`` to something like:

.. example::
   mongo://user:password@hostname:port/database/collection?authSource=avalon

or set ``PYPE_LOG_MONGO_HOST`` and other variables.
See :func:`_mongo_settings`

Best place for it is in ``repos/pype-config/environments/global.json``
"""


import logging
import os
import sys
import datetime
import time
import platform
import getpass
import socket
import traceback

from logging.handlers import TimedRotatingFileHandler

from . import terminal
from .mongo import (
    MongoEnvNotSet,
    decompose_url,
    compose_url,
    get_default_components
)

try:
    import log4mongo
    from log4mongo.handlers import MongoHandler
    from bson.objectid import ObjectId
    MONGO_PROCESS_ID = ObjectId()
except ImportError:
    _mongo_logging = False
else:
    _mongo_logging = True

try:
    unicode
    _unicode = True
except NameError:
    _unicode = False


PYPE_DEBUG = int(os.getenv("PYPE_DEBUG", "0"))
LOG_DATABASE_NAME = os.environ.get("PYPE_LOG_MONGO_DB") or "pype"
LOG_COLLECTION_NAME = os.environ.get("PYPE_LOG_MONGO_COL") or "logs"

system_name, pc_name = platform.uname()[:2]
host_name = socket.gethostname()
try:
    ip = socket.gethostbyname(host_name)
except socket.gaierror:
    ip = "127.0.0.1"

# Get process name
if len(sys.argv) > 0 and os.path.basename(sys.argv[0]) == "tray.py":
    process_name = "Tray"
else:
    try:
        import psutil
        process = psutil.Process(os.getpid())
        process_name = process.name()

    except ImportError:
        process_name = os.environ.get("AVALON_APP_NAME")
        if not process_name:
            process_name = os.path.basename(sys.executable)


def _log_mongo_components():
    mongo_url = os.environ.get("PYPE_LOG_MONGO_URL")
    if mongo_url is not None:
        components = decompose_url(mongo_url)
    else:
        components = get_default_components()
    return components


def _bootstrap_mongo_log(components=None):
    """
    This will check if database and collection for logging exist on server.
    """
    import pymongo

    if components is None:
        components = _log_mongo_components()

    if not components["host"]:
        # fail silently
        return

    timeout = int(os.environ.get("AVALON_TIMEOUT", 1000))
    kwargs = {
        "host": compose_url(**components),
        "serverSelectionTimeoutMS": timeout
    }

    port = components.get("port")
    if port is not None:
        kwargs["port"] = int(port)
    client = pymongo.MongoClient(**kwargs)
    logdb = client[LOG_DATABASE_NAME]

    collist = logdb.list_collection_names()
    if LOG_COLLECTION_NAME not in collist:
        logdb.create_collection(
            LOG_COLLECTION_NAME, capped=True, max=5000, size=1073741824
        )
    return logdb


class PypeStreamHandler(logging.StreamHandler):
    """ StreamHandler class designed to handle utf errors in python 2.x hosts.

    """

    def __init__(self, stream=None):
        super(PypeStreamHandler, self).__init__(stream)
        self.enabled = True

    def enable(self):
        """ Enable StreamHandler

            Used to silence output
        """
        self.enabled = True
        pass

    def disable(self):
        """ Disable StreamHandler

            Make StreamHandler output again
        """
        self.enabled = False

    def emit(self, record):
        if not self.enable:
            return
        try:
            msg = self.format(record)
            msg = terminal.log(msg)
            stream = self.stream
            fs = "%s\n"
            if not _unicode:  # if no unicode support...
                stream.write(fs % msg)
            else:
                try:
                    if (isinstance(msg, unicode) and  # noqa: F821
                            getattr(stream, 'encoding', None)):
                        ufs = u'%s\n'
                        try:
                            stream.write(ufs % msg)
                        except UnicodeEncodeError:
                            stream.write((ufs % msg).encode(stream.encoding))
                    else:
                        if (getattr(stream, 'encoding', 'utf-8')):
                            ufs = u'%s\n'
                            stream.write(ufs % unicode(msg))  # noqa: F821
                        else:
                            stream.write(fs % msg)
                except UnicodeError:
                    stream.write(fs % msg.encode("UTF-8"))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            print(repr(record))
            self.handleError(record)


class PypeFormatter(logging.Formatter):

    DFT = '%(levelname)s >>> { %(name)s }: [ %(message)s ]'
    default_formatter = logging.Formatter(DFT)

    def __init__(self, formats):
        super(PypeFormatter, self).__init__()
        self.formatters = {}
        for loglevel in formats:
            self.formatters[loglevel] = logging.Formatter(formats[loglevel])

    def format(self, record):
        formatter = self.formatters.get(record.levelno, self.default_formatter)

        _exc_info = record.exc_info
        record.exc_info = None

        out = formatter.format(record)
        record.exc_info = _exc_info

        if record.exc_info is not None:
            line_len = len(str(record.exc_info[1]))
            out = "{}\n{}\n{}\n{}\n{}".format(
                out,
                line_len * "=",
                str(record.exc_info[1]),
                line_len * "=",
                self.formatException(record.exc_info)
            )
        return out


class PypeMongoFormatter(logging.Formatter):

    DEFAULT_PROPERTIES = logging.LogRecord(
        '', '', '', '', '', '', '', '').__dict__.keys()

    def format(self, record):
        """Formats LogRecord into python dictionary."""
        # Standard document
        document = {
            'timestamp': datetime.datetime.now(),
            'level': record.levelname,
            'thread': record.thread,
            'threadName': record.threadName,
            'message': record.getMessage(),
            'loggerName': record.name,
            'fileName': record.pathname,
            'module': record.module,
            'method': record.funcName,
            'lineNumber': record.lineno,
            'process_id': MONGO_PROCESS_ID,
            'hostname': host_name,
            'hostip': ip,
            'username': getpass.getuser(),
            'system_name': system_name,
            'process_name': process_name
        }
        # Standard document decorated with exception info
        if record.exc_info is not None:
            document.update({
                'exception': {
                    'message': str(record.exc_info[1]),
                    'code': 0,
                    'stackTrace': self.formatException(record.exc_info)
                }
            })
        # Standard document decorated with extra contextual information
        if len(self.DEFAULT_PROPERTIES) != len(record.__dict__):
            contextual_extra = set(record.__dict__).difference(
                set(self.DEFAULT_PROPERTIES))
            if contextual_extra:
                for key in contextual_extra:
                    document[key] = record.__dict__[key]
        return document


class PypeLogger:

    PYPE_DEBUG = 0

    DFT = '%(levelname)s >>> { %(name)s }: [ %(message)s ] '
    DBG = "  - { %(name)s }: [ %(message)s ] "
    INF = ">>> [ %(message)s ] "
    WRN = "*** WRN: >>> { %(name)s }: [ %(message)s ] "
    ERR = "!!! ERR: %(asctime)s >>> { %(name)s }: [ %(message)s ] "
    CRI = "!!! CRI: %(asctime)s >>> { %(name)s }: [ %(message)s ] "

    FORMAT_FILE = {
        logging.INFO: INF,
        logging.DEBUG: DBG,
        logging.WARNING: WRN,
        logging.ERROR: ERR,
        logging.CRITICAL: CRI,
    }

    def __init__(self):
        self.PYPE_DEBUG = int(os.environ.get("PYPE_DEBUG", "0"))

    @staticmethod
    def get_file_path(host='pype'):

        ts = time.time()
        log_name = datetime.datetime.fromtimestamp(ts).strftime(
            '%Y-%m-%d'  # '%Y-%m-%d_%H-%M-%S'
        )

        logger_file_root = os.path.join(
            os.path.expanduser("~"),
            ".pype-setup"
        )

        logger_file_path = os.path.join(
            logger_file_root,
            "{}-{}.{}".format(host, log_name, 'log')
        )

        if not os.path.exists(logger_file_root):
            os.mkdir(logger_file_root)

        return logger_file_path

    def _get_file_handler(self, host):
        logger_file_path = PypeLogger.get_file_path(host)

        formatter = PypeFormatter(self.FORMAT_FILE)

        file_handler = TimedRotatingFileHandler(
            logger_file_path,
            when='midnight'
        )
        file_handler.set_name("PypeFileHandler")
        file_handler.setFormatter(formatter)
        return file_handler

    def _get_mongo_handler(self):
        components = _log_mongo_components()
        # Check existence of mongo connection before creating Mongo handler
        if log4mongo.handlers._connection is None:
            _bootstrap_mongo_log(components)

        kwargs = {
            "host": compose_url(**components),
            "database_name": LOG_DATABASE_NAME,
            "collection": LOG_COLLECTION_NAME,
            "username": components["username"],
            "password": components["password"],
            "capped": True,
            "formatter": PypeMongoFormatter()
        }
        if components["port"] is not None:
            kwargs["port"] = int(components["port"])
        if components["auth_db"]:
            kwargs["authentication_db"] = components["auth_db"]

        return MongoHandler(**kwargs)

    def _get_console_handler(self):

        formatter = PypeFormatter(self.FORMAT_FILE)
        console_handler = PypeStreamHandler()

        console_handler.set_name("PypeStreamHandler")
        console_handler.setFormatter(formatter)
        return console_handler

    def get_logger(self, name=None, host=None):
        logger = logging.getLogger(name or '__main__')

        if self.PYPE_DEBUG > 1:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        global _mongo_logging
        add_mongo_handler = _mongo_logging
        add_console_handler = True

        for handler in logger.handlers:
            if isinstance(handler, MongoHandler):
                add_mongo_handler = False
            elif isinstance(handler, PypeStreamHandler):
                add_console_handler = False

        if add_console_handler:
            logger.addHandler(self._get_console_handler())

        if add_mongo_handler:
            try:
                logger.addHandler(self._get_mongo_handler())

            except MongoEnvNotSet:
                # Skip if mongo environments are not set yet
                _mongo_logging = False

            except Exception:
                lines = traceback.format_exception(*sys.exc_info())
                for line in lines:
                    if line.endswith("\n"):
                        line = line[:-1]
                    terminal.echo(line)
                _mongo_logging = False

        return logger
