import os
import sys
import time
import functools
import logging
import pymongo
import ctypes
from uuid import uuid4

from avalon import schema


def extract_port_from_url(url):
    if sys.version_info[0] == 2:
        from urlparse import urlparse
    else:
        from urllib.parse import urlparse
    parsed_url = urlparse(url)
    if parsed_url.scheme is None:
        _url = "mongodb://{}".format(url)
        parsed_url = urlparse(_url)
    return parsed_url.port


def requires_install(func):
    func_obj = getattr(func, "__self__", None)

    @functools.wraps(func)
    def decorated(*args, **kwargs):
        if func_obj is not None:
            _obj = func_obj
        else:
            _obj = args[0]
        if not _obj.is_installed():
            if _obj.auto_install:
                _obj.install()
            else:
                raise IOError(
                    "'{}.{}()' requires to run install() first".format(
                        _obj.__class__.__name__, func.__name__
                    )
                )
        return func(*args, **kwargs)
    return decorated


def auto_reconnect(func):
    """Handling auto reconnect in 3 retry times"""
    retry_times = 3
    reconnect_msg = "Reconnecting..."
    func_obj = getattr(func, "__self__", None)

    @functools.wraps(func)
    def decorated(*args, **kwargs):
        if func_obj is not None:
            _obj = func_obj
        else:
            _obj = args[0]

        for retry in range(1, retry_times + 1):
            try:
                return func(*args, **kwargs)
            except pymongo.errors.AutoReconnect:
                if hasattr(_obj, "log"):
                    _obj.log.warning(reconnect_msg)
                else:
                    print(reconnect_msg)

                if retry >= retry_times:
                    raise
                time.sleep(0.1)
    return decorated


class PypeMongoConnection:
    """
        Connection to 'pype' database (not avalon). This database should be
        used for logs, configuration, upgrade patches etc.
        Code based on AvalonMongoConnection, but for separation of avalon-pype
        code is reproduced and simplified here.
    """
    _mongo_client = None
    _is_installed = False
    _databases = {}
    log = logging.getLogger("PypeMongoConnection")

    @classmethod
    def register_database(cls, dbcon):
        """
            Sets accessible database connection to _databases.
            One connection could potentially handle multiple databases (
            on same url).
        Args:
            dbcon:

        Returns:

        """
        if dbcon.id in cls._databases:
            return

        cls._databases[dbcon.id] = {
            "object": dbcon,
            "installed": False
        }

    @classmethod
    def database(cls):
        """
            Expects environment variable "PYPE_MONGO_DB_NAME" or 'pype' as
            a default.
        Returns:
           (pymongo.database)
        """
        return cls._mongo_client[os.getenv("PYPE_MONGO_DB_NAME") or "pype"]

    @classmethod
    def mongo_client(cls):
        """
        Returns:
            (pymongo.mongo_client)

        """
        return cls._mongo_client

    @classmethod
    def install(cls, dbcon):
        """
            Creates persistent connection to 'dbCon', registers it to
            _databases to be accessible by its 'uuid'.
        Args:
            dbcon (PypeMongoDB): similar to pymongo.database, database object
                used for operations like 'find', 'insert_one'.

        Returns:

        """
        if not cls._is_installed or cls._mongo_client is None:
            cls._mongo_client = cls.create_connection()
            cls._is_installed = True

        cls.register_database(dbcon)
        cls._databases[dbcon.id]["installed"] = True

        cls.check_db_existence()

    @classmethod
    def is_installed(cls, dbcon):
        """"
            Checks if connection to 'dbcon' database exists. (eg. there is
            mongoDB client connected to server and has connection to database)

            Returns:
                (boolean): true if connected
        """
        info = cls._databases.get(dbcon.id)
        if not info:
            return False
        return cls._databases[dbcon.id]["installed"]

    @classmethod
    def _uninstall(cls):
        """
            Closes client's connection to server.
        """
        try:
            cls._mongo_client.close()
        except AttributeError:
            pass
        cls._is_installed = False
        cls._mongo_client = None

    @classmethod
    def uninstall(cls, dbcon, force=False):
        """
            Deregisters connection to 'dbcon', if no more 'alive' databases
            present, it closes client connection.
            If 'force' all connected databases are deregistered and client
            closed.
        Args:
            dbcon (PypeMongoDB): enhance mongodb.database
            force (boolean):

        Returns:

        """
        if force:
            for key in cls._databases:
                cls._databases[key]["object"].uninstall()
            cls._uninstall()
            return

        cls._databases[dbcon.id]["installed"] = False

        cls.check_db_existence()

        any_is_installed = False
        for key in cls._databases:
            if cls._databases[key]["installed"]:
                any_is_installed = True
                break

        if not any_is_installed:
            cls._uninstall()

    @classmethod
    def check_db_existence(cls):
        """ Double check existence and 'livenes'' of registered databases.
            All non-existen databases are deregistered.
            Updates '_databases'.
        """
        items_to_pop = set()
        for db_id, info in cls._databases.items():
            obj = info["object"]
            # TODO check if should check for 1 or more
            cls.log.info(ctypes.c_long.from_address(id(obj)).value)
            if ctypes.c_long.from_address(id(obj)).value == 1:
                items_to_pop.add(db_id)

        for db_id in items_to_pop:
            cls._databases.pop(db_id, None)

    @classmethod
    def create_connection(cls):
        """
            Tries to create mongodb client connection to server host configured
            by environment variable 'PYPE_MONGO'.
        Returns:
            (pymongo.MongoClient) connected client
        Raises:
            IOError - if even after 3 retries host is not accessible
        """
        timeout = int(os.environ["AVALON_TIMEOUT"])
        mongo_url = os.environ["PYPE_MONGO"]
        kwargs = {
            "host": mongo_url,
            "serverSelectionTimeoutMS": timeout
        }

        port = extract_port_from_url(mongo_url)
        if port is not None:
            kwargs["port"] = int(port)

        mongo_client = pymongo.MongoClient(**kwargs)

        for _retry in range(3):
            try:
                t1 = time.time()
                mongo_client.server_info()

            except Exception:
                cls.log.warning("Retrying...")
                time.sleep(1)
                timeout *= 1.5

            else:
                break

        else:
            raise IOError((
                "ERROR: Couldn't connect to {} in less than {:.3f}ms"
            ).format(mongo_url, timeout))

        cls.log.info("Connected to {}, delay {:.3f}s".format(
            mongo_url, time.time() - t1
        ))
        return mongo_client


class PypeMongoDB:
    """ Enhanced wrapper around pymongo.database used for all operations
        based on pymongo.database.
        Has a functionality for auto_connect, parent mongo client is
        accessible.
    """
    def __init__(self, collection, auto_install=True):
        self._id = uuid4()
        self._database = None
        self.auto_install = auto_install
        self._collection = collection

        self.log = logging.getLogger(self.__class__.__name__)

    def __getattr__(self, attr_name):
        """
            All not explicitly implemented operations on pymongo.database
            are wrapped in 'auto_reconnect' decorator
        Args:
            attr_name (string): attribute from pymongo.database

        Returns:
            attribute or wrapped callable
        """
        print("attr_name:: {}".format(attr_name))
        self.log.debug("attr_name:: {}".format(attr_name))
        attr = None
        if self.is_installed() and self.auto_install:
            self.install()

        if self.is_installed():
            attr = getattr(
                self._database[self._collection],
                attr_name,
                None
            )

        if attr is None:
            # Reraise attribute error
            return self.__getattribute__(attr_name)

        # Decorate function
        if callable(attr):
            attr = auto_reconnect(attr)
        return attr

    @property
    def client(self):
        """
        Returns:
            pymongo.MongoClient
        """
        return PypeMongoConnection.mongo_client()

    @property
    def id(self):
        """
            Identifier of database
        Returns:
            (uuid4)
        """
        return self._id

    @property
    def database(self):
        if not self.is_installed() and self.auto_install:
            self.install()

        if self.is_installed():
            return self._database

        raise IOError(
            "'{}.database' requires to run install() first".format(
                self.__class__.__name__
            )
        )

    def is_installed(self):
        return PypeMongoConnection.is_installed(self)

    def install(self):
        """Establish a persistent connection to the database"""
        if self.is_installed():
            return

        PypeMongoConnection.install(self)

        self._database = PypeMongoConnection.database()

    def uninstall(self):
        """Close any connection to the database"""
        PypeMongoConnection.uninstall(self)
        self._database = None

    @auto_reconnect
    def insert_one(self, item, *args, **kwargs):
        assert isinstance(item, dict), "item must be of type <dict>"
        schema.validate(item)
        return self._database[self._collection].insert_one(
            item, *args, **kwargs
        )

    @auto_reconnect
    def insert_many(self, items, *args, **kwargs):
        # check if all items are valid
        assert isinstance(items, list), "`items` must be of type <list>"
        for item in items:
            assert isinstance(item, dict), "`item` must be of type <dict>"
            schema.validate(item)

        return self._database[self._collection].insert_many(
            items, *args, **kwargs
        )
