import os
import time
import functools
import logging
import pymongo
from uuid import uuid4

from . import schema


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


SESSION_CONTEXT_KEYS = (
    # Root directory of projects on disk
    "AVALON_PROJECTS",
    # Name of current Project
    "AVALON_PROJECT",
    # Name of current Asset
    "AVALON_ASSET",
    # Name of current task
    "AVALON_TASK",
    # Name of current app
    "AVALON_APP",
    # Path to working directory
    "AVALON_WORKDIR",
    # Optional path to scenes directory (see Work Files API)
    "AVALON_SCENEDIR"
)


def session_data_from_environment(context_keys=False):
    session_data = {}
    if context_keys:
        for key in SESSION_CONTEXT_KEYS:
            value = os.environ.get(key)
            session_data[key] = value or ""
    else:
        for key in SESSION_CONTEXT_KEYS:
            session_data[key] = None

    for key, default_value in (
        # Name of Avalon in graphical user interfaces
        # Use this to customise the visual appearance of Avalon
        # to better integrate with your surrounding pipeline
        ("AVALON_LABEL", "Avalon"),

        # Used during any connections to the outside world
        ("AVALON_TIMEOUT", "1000"),

        # Name of database used in MongoDB
        ("AVALON_DB", "avalon"),
    ):
        value = os.environ.get(key) or default_value
        if value is not None:
            session_data[key] = value

    return session_data


class AvalonMongoDB:
    def __init__(self, session=None, auto_install=True):
        self._id = uuid4()
        self._database = None
        self.auto_install = auto_install
        self._installed = False

        if session is None:
            session = session_data_from_environment(context_keys=False)

        self.Session = session

        self.log = logging.getLogger(self.__class__.__name__)

    def __getattr__(self, attr_name):
        attr = None
        if not self.is_installed() and self.auto_install:
            self.install()

        if not self.is_installed():
            raise IOError(
                "'{}.{}()' requires to run install() first".format(
                    self.__class__.__name__, attr_name
                )
            )

        project_name = self.active_project()
        if project_name is None:
            raise ValueError(
                "Value of 'Session[\"AVALON_PROJECT\"]' is not set."
            )

        collection = self._database[project_name]
        not_set = object()
        attr = getattr(collection, attr_name, not_set)

        if attr is not_set:
            # Raise attribute error
            raise AttributeError(
                "{} has no attribute '{}'.".format(
                    collection.__class__.__name__, attr_name
                )
            )

        # Decorate function
        if callable(attr):
            attr = auto_reconnect(attr)
        return attr

    @property
    def mongo_client(self):
        from openpype.lib import OpenPypeMongoConnection

        return OpenPypeMongoConnection.get_mongo_client()

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
        return self._installed

    def install(self):
        """Establish a persistent connection to the database"""
        if self.is_installed():
            return

        self._installed = True
        self._database = self.mongo_client[str(os.environ["AVALON_DB"])]

    def uninstall(self):
        """Close any connection to the database"""
        self._installed = False
        self._database = None

    @requires_install
    def active_project(self):
        """Return the name of the active project"""
        return self.Session["AVALON_PROJECT"]

    def current_project(self):
        """Currently set project in Session without triggering installation."""
        return self.Session.get("AVALON_PROJECT")

    @requires_install
    @auto_reconnect
    def projects(self, projection=None, only_active=True):
        """Iter project documents

        Args:
            projection (optional): MongoDB query projection operation
            only_active (optional): Skip inactive projects, default True.

        Returns:
            Project documents iterator

        """
        query_filter = {"type": "project"}
        if only_active:
            query_filter.update({
                "$or": [
                    {"data.active": {"$exists": 0}},
                    {"data.active": True},
                ]
            })

        for project_name in self._database.collection_names():
            if project_name in ("system.indexes",):
                continue

            # Each collection will have exactly one project document

            doc = self._database[project_name].find_one(
                query_filter, projection=projection
            )
            if doc is not None:
                yield doc

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

            if document.get("type") == "hero_version":
                _document = self.find_one({"_id": document["version_id"]})
                document["data"] = _document["data"]

            parents.append(document)

        return parents
