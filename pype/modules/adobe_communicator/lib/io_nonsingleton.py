"""
Wrapper around interactions with the database

Copy of io module in avalon-core.
 - In this case not working as singleton with api.Session!
"""

import os
import time
import errno
import shutil
import logging
import tempfile
import functools
import contextlib

from avalon import schema
from avalon.vendor import requests

# Third-party dependencies
import pymongo


def auto_reconnect(func):
    """Handling auto reconnect in 3 retry times"""
    @functools.wraps(func)
    def decorated(*args, **kwargs):
        object = args[0]
        for retry in range(3):
            try:
                return func(*args, **kwargs)
            except pymongo.errors.AutoReconnect:
                object.log.error("Reconnecting..")
                time.sleep(0.1)
        else:
            raise

    return decorated


class DbConnector(object):

    log = logging.getLogger(__name__)

    def __init__(self):
            self.Session = {}
            self._mongo_client = None
            self._sentry_client = None
            self._sentry_logging_handler = None
            self._database = None
            self._is_installed = False

    def __getitem__(self, key):
        # gives direct access to collection withou setting `active_table`
        return self._database[key]

    def __getattribute__(self, attr):
        # not all methods of PyMongo database are implemented with this it is
        # possible to use them too
        try:
            return super(DbConnector, self).__getattribute__(attr)
        except AttributeError:
            cur_proj = self.Session["AVALON_PROJECT"]
            return self._database[cur_proj].__getattribute__(attr)

    def install(self):
        """Establish a persistent connection to the database"""
        if self._is_installed:
            return

        logging.basicConfig()
        self.Session.update(self._from_environment())

        timeout = int(self.Session["AVALON_TIMEOUT"])
        self._mongo_client = pymongo.MongoClient(
            self.Session["AVALON_MONGO"], serverSelectionTimeoutMS=timeout)

        for retry in range(3):
            try:
                t1 = time.time()
                self._mongo_client.server_info()

            except Exception:
                self.log.error("Retrying..")
                time.sleep(1)
                timeout *= 1.5

            else:
                break

        else:
            raise IOError(
                "ERROR: Couldn't connect to %s in "
                "less than %.3f ms" % (self.Session["AVALON_MONGO"], timeout))

        self.log.info("Connected to %s, delay %.3f s" % (
            self.Session["AVALON_MONGO"], time.time() - t1))

        self._install_sentry()

        self._database = self._mongo_client[self.Session["AVALON_DB"]]
        self._is_installed = True

    def _install_sentry(self):
        if "AVALON_SENTRY" not in self.Session:
            return

        try:
            from raven import Client
            from raven.handlers.logging import SentryHandler
            from raven.conf import setup_logging
        except ImportError:
            # Note: There was a Sentry address in this Session
            return self.log.warning("Sentry disabled, raven not installed")

        client = Client(self.Session["AVALON_SENTRY"])

        # Transmit log messages to Sentry
        handler = SentryHandler(client)
        handler.setLevel(logging.WARNING)

        setup_logging(handler)

        self._sentry_client = client
        self._sentry_logging_handler = handler
        self.log.info(
            "Connected to Sentry @ %s" % self.Session["AVALON_SENTRY"]
        )

    def _from_environment(self):
        Session = {
            item[0]: os.getenv(item[0], item[1])
            for item in (
                # Root directory of projects on disk
                ("AVALON_PROJECTS", None),

                # Name of current Project
                ("AVALON_PROJECT", ""),

                # Name of current Asset
                ("AVALON_ASSET", ""),

                # Name of current silo
                ("AVALON_SILO", ""),

                # Name of current task
                ("AVALON_TASK", None),

                # Name of current app
                ("AVALON_APP", None),

                # Path to working directory
                ("AVALON_WORKDIR", None),

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

                # Enable features not necessarily stable. The user's own risk
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
                ("AVALON_DEBUG", None),

            ) if os.getenv(item[0], item[1]) is not None
        }

        Session["schema"] = "avalon-core:session-2.0"
        try:
            schema.validate(Session)
        except schema.ValidationError as e:
            # TODO(marcus): Make this mandatory
            self.log.warning(e)

        return Session

    def uninstall(self):
        """Close any connection to the database"""
        try:
            self._mongo_client.close()
        except AttributeError:
            pass

        self._mongo_client = None
        self._database = None
        self._is_installed = False

    def active_project(self):
        """Return the name of the active project"""
        return self.Session["AVALON_PROJECT"]

    def activate_project(self, project_name):
        self.Session["AVALON_PROJECT"] = project_name

    def projects(self):
        """List available projects

        Returns:
            list of project documents

        """

        collection_names = self.collections()
        for project in collection_names:
            if project in ("system.indexes",):
                continue

            # Each collection will have exactly one project document
            document = self.find_project(project)

            if document is not None:
                yield document

    def locate(self, path):
        """Traverse a hierarchy from top-to-bottom

        Example:
            representation = locate(["hulk", "Bruce", "modelDefault", 1, "ma"])

        Returns:
            representation (ObjectId)

        """

        components = zip(
            ("project", "asset", "subset", "version", "representation"),
            path
        )

        parent = None
        for type_, name in components:
            latest = (type_ == "version") and name in (None, -1)

            try:
                if latest:
                    parent = self.find_one(
                        filter={
                            "type": type_,
                            "parent": parent
                        },
                        projection={"_id": 1},
                        sort=[("name", -1)]
                    )["_id"]
                else:
                    parent = self.find_one(
                        filter={
                            "type": type_,
                            "name": name,
                            "parent": parent
                        },
                        projection={"_id": 1},
                    )["_id"]

            except TypeError:
                return None

        return parent

    @auto_reconnect
    def collections(self):
        return self._database.collection_names()

    @auto_reconnect
    def find_project(self, project):
        return self._database[project].find_one({"type": "project"})

    @auto_reconnect
    def insert_one(self, item):
        assert isinstance(item, dict), "item must be of type <dict>"
        schema.validate(item)
        return self._database[self.Session["AVALON_PROJECT"]].insert_one(item)

    @auto_reconnect
    def insert_many(self, items, ordered=True):
        # check if all items are valid
        assert isinstance(items, list), "`items` must be of type <list>"
        for item in items:
            assert isinstance(item, dict), "`item` must be of type <dict>"
            schema.validate(item)

        return self._database[self.Session["AVALON_PROJECT"]].insert_many(
            items,
            ordered=ordered)

    @auto_reconnect
    def find(self, filter, projection=None, sort=None):
        return self._database[self.Session["AVALON_PROJECT"]].find(
            filter=filter,
            projection=projection,
            sort=sort
        )

    @auto_reconnect
    def find_one(self, filter, projection=None, sort=None):
        assert isinstance(filter, dict), "filter must be <dict>"

        return self._database[self.Session["AVALON_PROJECT"]].find_one(
            filter=filter,
            projection=projection,
            sort=sort
        )

    @auto_reconnect
    def save(self, *args, **kwargs):
        return self._database[self.Session["AVALON_PROJECT"]].save(
            *args, **kwargs)

    @auto_reconnect
    def replace_one(self, filter, replacement):
        return self._database[self.Session["AVALON_PROJECT"]].replace_one(
            filter, replacement)

    @auto_reconnect
    def update_many(self, filter, update):
        return self._database[self.Session["AVALON_PROJECT"]].update_many(
            filter, update)

    @auto_reconnect
    def distinct(self, *args, **kwargs):
        return self._database[self.Session["AVALON_PROJECT"]].distinct(
            *args, **kwargs)

    @auto_reconnect
    def drop(self, *args, **kwargs):
        return self._database[self.Session["AVALON_PROJECT"]].drop(
            *args, **kwargs)

    @auto_reconnect
    def delete_many(self, *args, **kwargs):
        return self._database[self.Session["AVALON_PROJECT"]].delete_many(
            *args, **kwargs)

    def parenthood(self, document):
        assert document is not None, "This is a bug"

        parents = list()

        while document.get("parent") is not None:
            document = self.find_one({"_id": document["parent"]})

            if document is None:
                break

            parents.append(document)

        return parents

    @contextlib.contextmanager
    def tempdir(self):
        tempdir = tempfile.mkdtemp()
        try:
            yield tempdir
        finally:
            shutil.rmtree(tempdir)

    def download(self, src, dst):
        """Download `src` to `dst`

        Arguments:
            src (str): URL to source file
            dst (str): Absolute path to destination file

        Yields tuple (progress, error):
            progress (int): Between 0-100
            error (Exception): Any exception raised when first making connection

        """

        try:
            response = requests.get(
                src,
                stream=True,
                auth=requests.auth.HTTPBasicAuth(
                    self.Session["AVALON_USERNAME"],
                    self.Session["AVALON_PASSWORD"]
                )
            )
        except requests.ConnectionError as e:
            yield None, e
            return

        with self.tempdir() as dirname:
            tmp = os.path.join(dirname, os.path.basename(src))

            with open(tmp, "wb") as f:
                total_length = response.headers.get("content-length")

                if total_length is None:  # no content length header
                    f.write(response.content)
                else:
                    downloaded = 0
                    total_length = int(total_length)
                    for data in response.iter_content(chunk_size=4096):
                        downloaded += len(data)
                        f.write(data)

                        yield int(100.0 * downloaded / total_length), None

            try:
                os.makedirs(os.path.dirname(dst))
            except OSError as e:
                # An already existing destination directory is fine.
                if e.errno != errno.EEXIST:
                    raise

            shutil.copy(tmp, dst)
