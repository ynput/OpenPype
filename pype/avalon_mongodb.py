# TODO move to avalon
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


def requires_install(func, obj=None):
    @functools.wraps(func)
    def decorated(*args, **kwargs):
        if obj is not None:
            _obj = obj
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


def auto_reconnect(func, obj=None):
    """Handling auto reconnect in 3 retry times"""
    retry_times = 3
    reconnect_msg = "Reconnecting..."

    @functools.wraps(func)
    def decorated(*args, **kwargs):
        if obj is not None:
            _obj = obj
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


SESSION_CONTEXT_KEYS = (
    # Root directory of projects on disk
    "AVALON_PROJECTS",
    # Name of current Project
    "AVALON_PROJECT",
    # Name of current Asset
    "AVALON_ASSET",
    # Name of current silo
    "AVALON_SILO",
    # Name of current task
    "AVALON_TASK",
    # Name of current app
    "AVALON_APP",
    # Path to working directory
    "AVALON_WORKDIR",
    # Optional path to scenes directory (see Work Files API)
    "AVALON_SCENEDIR",
    # Optional hierarchy for the current Asset. This can be referenced
    # as `{hierarchy}` in your file templates.
    # This will be (re-)computed when you switch the context to another
    # asset. It is computed by checking asset['data']['parents'] and
    # joining those together with `os.path.sep`.
    # E.g.: ['ep101', 'scn0010'] -> 'ep101/scn0010'.
    "AVALON_HIERARCHY"
)


def session_data_from_environment(global_keys=True, context_keys=False):
    session_data = {}
    if context_keys:
        for key in SESSION_CONTEXT_KEYS:
            value = os.environ.get(key)
            session_data[key] = value or ""

    if not global_keys:
        return session_data

    for key, default_value in (
        # Name of current Config
        # TODO(marcus): Establish a suitable default config
        ("AVALON_CONFIG", "no_config"),

        # Name of Avalon in graphical user interfaces
        # Use this to customise the visual appearance of Avalon
        # to better integrate with your surrounding pipeline
        ("AVALON_LABEL", "Avalon"),

        # Used during any connections to the outside world
        ("AVALON_TIMEOUT", "1000"),

        # Address to Asset Database
        ("AVALON_MONGO", "mongodb://localhost:27017"),

        # Name of database used in MongoDB
        ("AVALON_DB", "avalon"),

        # Address to Sentry
        ("AVALON_SENTRY", None),

        # Address to Deadline Web Service
        # E.g. http://192.167.0.1:8082
        ("AVALON_DEADLINE", None),

        # Enable features not necessarily stable, at the user's own risk
        ("AVALON_EARLY_ADOPTER", None),

        # Address of central asset repository, contains
        # the following interface:
        #   /upload
        #   /download
        #   /manager (optional)
        ("AVALON_LOCATION", "http://127.0.0.1"),

        # Boolean of whether to upload published material
        # to central asset repository
        ("AVALON_UPLOAD", None),

        # Generic username and password
        ("AVALON_USERNAME", "avalon"),
        ("AVALON_PASSWORD", "secret"),

        # Unique identifier for instances in working files
        ("AVALON_INSTANCE_ID", "avalon.instance"),
        ("AVALON_CONTAINER_ID", "avalon.container"),

        # Enable debugging
        ("AVALON_DEBUG", None)
    ):
        value = os.environ.get(key) or default_value
        if value is not None:
            session_data[key] = value

    return session_data


class AvalonMongoConnection:
    _mongo_client = None
    _is_installed = False
    _databases = {}
    log = logging.getLogger("AvalonMongoConnection")

    @classmethod
    def register_database(cls, dbcon):
        if dbcon.id in cls._databases:
            return

        cls._databases[dbcon.id] = {
            "object": dbcon,
            "installed": False
        }

    @classmethod
    def database(cls):
        return cls._mongo_client[os.environ["AVALON_DB"]]

    @classmethod
    def install(cls, dbcon):
        if not cls._is_installed or cls._mongo_client is None:
            cls._mongo_client = cls.create_connection()
            cls._is_installed = True

        cls.register_database(dbcon)
        cls._databases[dbcon.id]["installed"] = True

        cls.check_db_existence()

    @classmethod
    def is_installed(cls, dbcon):
        info = cls._databases.get(dbcon.id)
        if not info:
            return False
        return cls._databases[dbcon.id]["installed"]

    @classmethod
    def _uninstall(cls):
        try:
            cls._mongo_client.close()
        except AttributeError:
            pass
        cls._is_installed = False
        cls._mongo_client = None

    @classmethod
    def uninstall(cls, dbcon, force=False):
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
        timeout = int(os.environ["AVALON_TIMEOUT"])
        mongo_url = os.environ["AVALON_MONGO"]
        kwargs = {
            "host": mongo_url,
            "serverSelectionTimeoutMS": timeout
        }

        port = extract_port_from_url(mongo_url)
        if port is not None:
            kwargs["port"] = int(port)

        mongo_client = pymongo.MongoClient(**kwargs)

        for retry in range(3):
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


class AvalonMongoDB:
    def __init__(self, session=None, auto_install=True):
        self._id = uuid4()
        self._database = None
        self.auto_install = auto_install

        if session is None:
            session = session_data_from_environment(context_keys=False)

        self.Session = session

        self.log = logging.getLogger(self.__class__.__name__)

    def __getattr__(self, attr_name):
        attr = None
        if self.is_installed() and self.auto_install:
            self.install()

        if self.is_installed():
            attr = getattr(
                self._database[self.active_project()],
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
    def id(self):
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
        return AvalonMongoConnection.is_installed(self)

    def install(self):
        """Establish a persistent connection to the database"""
        if self.is_installed():
            return

        AvalonMongoConnection.install(self)

        self._database = AvalonMongoConnection.database()

    def uninstall(self):
        """Close any connection to the database"""
        try:
            self._mongo_client.close()
        except AttributeError:
            pass

        AvalonMongoConnection.uninstall(self)
        self._database = None

    @requires_install
    def active_project(self):
        """Return the name of the active project"""
        return self.Session["AVALON_PROJECT"]

    @requires_install
    @auto_reconnect
    def projects(self):
        """List available projects

        Returns:
            list of project documents

        """
        for project_name in self._database.collection_names():
            if project_name in ("system.indexes",):
                continue

            # Each collection will have exactly one project document
            document = self._database[project_name].find_one({
                "type": "project"
            })
            if document is not None:
                yield document

    @auto_reconnect
    def insert_one(self, item, *args, **kwargs):
        assert isinstance(item, dict), "item must be of type <dict>"
        schema.validate(item)
        return self._database[self.active_project()].insert_one(
            item, *args, **kwargs
        )

    @auto_reconnect
    def insert_many(self, items, *args, **kwargs):
        # check if all items are valid
        assert isinstance(items, list), "`items` must be of type <list>"
        for item in items:
            assert isinstance(item, dict), "`item` must be of type <dict>"
            schema.validate(item)

        return self._database[self.active_project()].insert_many(
            items, *args, **kwargs
        )

    def parenthood(self, document):
        assert document is not None, "This is a bug"

        parents = list()

        while document.get("parent") is not None:
            document = self.find_one({"_id": document["parent"]})
            if document is None:
                break

            if document.get("type") == "master_version":
                _document = self.find_one({"_id": document["version_id"]})
                document["data"] = _document["data"]

            parents.append(document)

        return parents
