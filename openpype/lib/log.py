"""
Logging to console and to mongo. For mongo logging, you need to set either
``OPENPYPE_LOG_MONGO_URL`` to something like:

.. example::
   mongo://user:password@hostname:port/database/collection?authSource=avalon

or set ``OPENPYPE_LOG_MONGO_HOST`` and other variables.
See :func:`_mongo_settings`

Best place for it is in ``repos/pype-config/environments/global.json``
"""


import datetime
import getpass
import logging
import os
import platform
import socket
import sys
import time
import traceback
import threading
import copy

from . import Terminal
from .mongo import (
    MongoEnvNotSet,
    get_default_components,
    OpenPypeMongoConnection
)
try:
    import log4mongo
    from log4mongo.handlers import MongoHandler
except ImportError:
    log4mongo = None
    MongoHandler = type("NOT_SET", (), {})

# Check for `unicode` in builtins
USE_UNICODE = hasattr(__builtins__, "unicode")


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
            msg = Terminal.log(msg)
            stream = self.stream
            if stream is None:
                return
            fs = "%s\n"
            # if no unicode support...
            if not USE_UNICODE:
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

        except OSError:
            self.handleError(record)

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
            if line_len > 30:
                line_len = 30
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
            'lineNumber': record.lineno
        }
        document.update(PypeLogger.get_process_data())

        # Standard document decorated with exception info
        if record.exc_info is not None:
            document['exception'] = {
                'message': str(record.exc_info[1]),
                'code': 0,
                'stackTrace': self.formatException(record.exc_info)
            }

        # Standard document decorated with extra contextual information
        if len(self.DEFAULT_PROPERTIES) != len(record.__dict__):
            contextual_extra = set(record.__dict__).difference(
                set(self.DEFAULT_PROPERTIES))
            if contextual_extra:
                for key in contextual_extra:
                    document[key] = record.__dict__[key]
        return document


class PypeLogger:
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

    # Is static class initialized
    bootstraped = False
    initialized = False
    _init_lock = threading.Lock()

    # Defines if mongo logging should be used
    use_mongo_logging = None
    mongo_process_id = None

    # Backwards compatibility - was used in start.py
    # TODO remove when all old builds are replaced with new one
    #   not using 'log_mongo_url_components'
    log_mongo_url_components = None

    # Database name in Mongo
    log_database_name = os.environ["OPENPYPE_DATABASE_NAME"]
    # Collection name under database in Mongo
    log_collection_name = "logs"

    # Logging level - OPENPYPE_LOG_LEVEL
    log_level = None

    # Data same for all record documents
    process_data = None
    # Cached process name or ability to set different process name
    _process_name = None

    @classmethod
    def get_logger(cls, name=None, _host=None):
        if not cls.initialized:
            cls.initialize()

        logger = logging.getLogger(name or "__main__")

        logger.setLevel(cls.log_level)

        add_mongo_handler = cls.use_mongo_logging
        add_console_handler = True

        for handler in logger.handlers:
            if isinstance(handler, MongoHandler):
                add_mongo_handler = False
            elif isinstance(handler, PypeStreamHandler):
                add_console_handler = False

        if add_console_handler:
            logger.addHandler(cls._get_console_handler())

        if add_mongo_handler:
            try:
                handler = cls._get_mongo_handler()
                if handler:
                    logger.addHandler(handler)

            except MongoEnvNotSet:
                # Skip if mongo environments are not set yet
                cls.use_mongo_logging = False

            except Exception:
                lines = traceback.format_exception(*sys.exc_info())
                for line in lines:
                    if line.endswith("\n"):
                        line = line[:-1]
                    Terminal.echo(line)
                cls.use_mongo_logging = False

        # Do not propagate logs to root logger
        logger.propagate = False

        if _host is not None:
            # Warn about deprecated argument
            # TODO remove backwards compatibility of host argument which is
            # not used for more than a year
            logger.warning(
                "Logger \"{}\" is using argument `host` on `get_logger`"
                " which is deprecated. Please remove as backwards"
                " compatibility will be removed soon."
            )
        return logger

    @classmethod
    def _get_mongo_handler(cls):
        cls.bootstrap_mongo_log()

        if not cls.use_mongo_logging:
            return

        components = get_default_components()
        kwargs = {
            "host": components["host"],
            "database_name": cls.log_database_name,
            "collection": cls.log_collection_name,
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

    @classmethod
    def _get_console_handler(cls):
        formatter = PypeFormatter(cls.FORMAT_FILE)
        console_handler = PypeStreamHandler()

        console_handler.set_name("PypeStreamHandler")
        console_handler.setFormatter(formatter)
        return console_handler

    @classmethod
    def initialize(cls):
        # TODO update already created loggers on re-initialization
        if not cls._init_lock.locked():
            with cls._init_lock:
                cls._initialize()
        else:
            # If lock is locked wait until is finished
            while cls._init_lock.locked():
                time.sleep(0.1)

    @classmethod
    def _initialize(cls):
        # Change initialization state to prevent runtime changes
        # if is executed during runtime
        cls.initialized = False
        cls.log_mongo_url_components = get_default_components()

        # Define if should logging to mongo be used
        use_mongo_logging = bool(log4mongo is not None)
        if use_mongo_logging:
            use_mongo_logging = os.environ.get("OPENPYPE_LOG_TO_SERVER") == "1"

        # Set mongo id for process (ONLY ONCE)
        if use_mongo_logging and cls.mongo_process_id is None:
            try:
                from bson.objectid import ObjectId
            except Exception:
                use_mongo_logging = False

            # Check if mongo id was passed with environments and pop it
            # - This is for subprocesses that are part of another process
            #   like Ftrack event server has 3 other subprocesses that should
            #   use same mongo id
            if use_mongo_logging:
                mongo_id = os.environ.pop("OPENPYPE_PROCESS_MONGO_ID", None)
                if not mongo_id:
                    # Create new object id
                    mongo_id = ObjectId()
                else:
                    # Convert string to ObjectId object
                    mongo_id = ObjectId(mongo_id)
                cls.mongo_process_id = mongo_id

        # Store result to class definition
        cls.use_mongo_logging = use_mongo_logging

        # Define what is logging level
        log_level = os.getenv("OPENPYPE_LOG_LEVEL")
        if not log_level:
            # Check OPENPYPE_DEBUG for backwards compatibility
            op_debug = os.getenv("OPENPYPE_DEBUG")
            if op_debug and int(op_debug) > 0:
                log_level = 10
            else:
                log_level = 20
        cls.log_level = int(log_level)

        if not os.environ.get("OPENPYPE_MONGO"):
            cls.use_mongo_logging = False

        # Mark as initialized
        cls.initialized = True

    @classmethod
    def get_process_data(cls):
        """Data about current process which should be same for all records.

        Process data are used for each record sent to mongo database.
        """
        if cls.process_data is not None:
            return copy.deepcopy(cls.process_data)

        if not cls.initialized:
            cls.initialize()

        host_name = socket.gethostname()
        try:
            host_ip = socket.gethostbyname(host_name)
        except socket.gaierror:
            host_ip = "127.0.0.1"

        process_name = cls.get_process_name()

        cls.process_data = {
            "process_id": cls.mongo_process_id,
            "hostname": host_name,
            "hostip": host_ip,
            "username": getpass.getuser(),
            "system_name": platform.system(),
            "process_name": process_name
        }
        return copy.deepcopy(cls.process_data)

    @classmethod
    def set_process_name(cls, process_name):
        """Set process name for mongo logs."""
        # Just change the attribute
        cls._process_name = process_name
        # Update process data if are already set
        if cls.process_data is not None:
            cls.process_data["process_name"] = process_name

    @classmethod
    def get_process_name(cls):
        """Process name that is like "label" of a process.

        Pype's logging can be used from pype itseld of from hosts. Even in Pype
        it's good to know if logs are from Pype tray or from pype's event
        server. This should help to identify that information.
        """
        if cls._process_name is not None:
            return cls._process_name

        # Get process name
        process_name = os.environ.get("AVALON_APP_NAME")
        if not process_name:
            try:
                import psutil
                process = psutil.Process(os.getpid())
                process_name = process.name()

            except ImportError:
                pass

        if not process_name:
            process_name = os.path.basename(sys.executable)

        cls._process_name = process_name
        return cls._process_name

    @classmethod
    def bootstrap_mongo_log(cls):
        """Prepare mongo logging."""
        if cls.bootstraped:
            return

        if not cls.initialized:
            cls.initialize()

        if not cls.use_mongo_logging:
            return

        client = log4mongo.handlers._connection
        if not client:
            client = cls.get_log_mongo_connection()
            # Set the client inside log4mongo handlers to not create another
            # mongo db connection.
            log4mongo.handlers._connection = client

        logdb = client[cls.log_database_name]

        collist = logdb.list_collection_names()
        if cls.log_collection_name not in collist:
            logdb.create_collection(
                cls.log_collection_name,
                capped=True,
                max=5000,
                size=1073741824
            )
        cls.bootstraped = True

    @classmethod
    def get_log_mongo_connection(cls):
        """Mongo connection that allows to get to log collection.

        This is implemented to prevent multiple connections to mongo from same
        process.
        """
        if not cls.initialized:
            cls.initialize()

        return OpenPypeMongoConnection.get_mongo_client()


def timeit(method):
    """Print time in function.

    For debugging.

    """
    log = logging.getLogger()

    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            log.debug('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
            print('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result
    return timed
