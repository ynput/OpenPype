import os
import sys
import time
import logging
import pymongo
import certifi

from bson.json_util import (
    loads,
    dumps,
    CANONICAL_JSON_OPTIONS
)

from openpype import AYON_SERVER_ENABLED
if sys.version_info[0] == 2:
    from urlparse import urlparse, parse_qs
else:
    from urllib.parse import urlparse, parse_qs


class MongoEnvNotSet(Exception):
    pass


def documents_to_json(docs):
    """Convert documents to json string.

    Args:
        Union[list[dict[str, Any]], dict[str, Any]]: Document/s to convert to
            json string.

    Returns:
        str: Json string with mongo documents.
    """

    return dumps(docs, json_options=CANONICAL_JSON_OPTIONS)


def load_json_file(filepath):
    """Load mongo documents from a json file.

    Args:
        filepath (str): Path to a json file.

    Returns:
        Union[dict[str, Any], list[dict[str, Any]]]: Loaded content from a
            json file.
    """

    if not os.path.exists(filepath):
        raise ValueError("Path {} was not found".format(filepath))

    with open(filepath, "r") as stream:
        content = stream.read()
    return loads("".join(content))


def get_project_database_name():
    """Name of database name where projects are available.

    Returns:
        str: Name of database name where projects are.
    """

    return os.environ.get("AVALON_DB") or "avalon"


def _decompose_url(url):
    """Decompose mongo url to basic components.

    Used for creation of MongoHandler which expect mongo url components as
    separated kwargs. Components are at the end not used as we're setting
    connection directly this is just a dumb components for MongoHandler
    validation pass.
    """

    # Use first url from passed url
    #   - this is because it is possible to pass multiple urls for multiple
    #       replica sets which would crash on urlparse otherwise
    #   - please don't use comma in username of password
    url = url.split(",")[0]
    components = {
        "scheme": None,
        "host": None,
        "port": None,
        "username": None,
        "password": None,
        "auth_db": None
    }

    result = urlparse(url)
    if result.scheme is None:
        _url = "mongodb://{}".format(url)
        result = urlparse(_url)

    components["scheme"] = result.scheme
    components["host"] = result.hostname
    try:
        components["port"] = result.port
    except ValueError:
        raise RuntimeError("invalid port specified")
    components["username"] = result.username
    components["password"] = result.password

    try:
        components["auth_db"] = parse_qs(result.query)['authSource'][0]
    except KeyError:
        # no auth db provided, mongo will use the one we are connecting to
        pass

    return components


def get_default_components():
    mongo_url = os.environ.get("OPENPYPE_MONGO")
    if mongo_url is None:
        raise MongoEnvNotSet(
            "URL for Mongo logging connection is not set."
        )
    return _decompose_url(mongo_url)


def should_add_certificate_path_to_mongo_url(mongo_url):
    """Check if should add ca certificate to mongo url.

    Since 30.9.2021 cloud mongo requires newer certificates that are not
    available on most of workstation. This adds path to certifi certificate
    which is valid for it. To add the certificate path url must have scheme
    'mongodb+srv' or has 'ssl=true' or 'tls=true' in url query.
    """

    parsed = urlparse(mongo_url)
    query = parse_qs(parsed.query)
    lowered_query_keys = set(key.lower() for key in query.keys())
    add_certificate = False
    # Check if url 'ssl' or 'tls' are set to 'true'
    for key in ("ssl", "tls"):
        if key in query and "true" in query[key]:
            add_certificate = True
            break

    # Check if url contains 'mongodb+srv'
    if not add_certificate and parsed.scheme == "mongodb+srv":
        add_certificate = True

    # Check if url does already contain certificate path
    if add_certificate and "tlscafile" in lowered_query_keys:
        add_certificate = False

    return add_certificate


def validate_mongo_connection(mongo_uri):
    """Check if provided mongodb URL is valid.

    Args:
        mongo_uri (str): URL to validate.

    Raises:
        ValueError: When port in mongo uri is not valid.
        pymongo.errors.InvalidURI: If passed mongo is invalid.
        pymongo.errors.ServerSelectionTimeoutError: If connection timeout
            passed so probably couldn't connect to mongo server.

    """

    client = OpenPypeMongoConnection.create_connection(
        mongo_uri, retry_attempts=1
    )
    client.close()


class OpenPypeMongoConnection:
    """Singleton MongoDB connection.

    Keeps MongoDB connections by url.
    """

    mongo_clients = {}
    log = logging.getLogger("OpenPypeMongoConnection")

    @staticmethod
    def get_default_mongo_url():
        return os.environ["OPENPYPE_MONGO"]

    @classmethod
    def get_mongo_client(cls, mongo_url=None):
        if mongo_url is None:
            mongo_url = cls.get_default_mongo_url()

        connection = cls.mongo_clients.get(mongo_url)
        if connection:
            # Naive validation of existing connection
            try:
                connection.server_info()
                with connection.start_session():
                    pass
            except Exception:
                connection = None

        if not connection:
            cls.log.debug("Creating mongo connection to {}".format(mongo_url))
            connection = cls.create_connection(mongo_url)
            cls.mongo_clients[mongo_url] = connection

        return connection

    @classmethod
    def create_connection(cls, mongo_url, timeout=None, retry_attempts=None):
        if AYON_SERVER_ENABLED:
            raise RuntimeError("Created mongo connection  in AYON mode")
        parsed = urlparse(mongo_url)
        # Force validation of scheme
        if parsed.scheme not in ["mongodb", "mongodb+srv"]:
            raise pymongo.errors.InvalidURI((
                "Invalid URI scheme:"
                " URI must begin with 'mongodb://' or 'mongodb+srv://'"
            ))

        if timeout is None:
            timeout = int(os.environ.get("AVALON_TIMEOUT") or 1000)

        kwargs = {
            "serverSelectionTimeoutMS": timeout
        }
        if should_add_certificate_path_to_mongo_url(mongo_url):
            kwargs["ssl_ca_certs"] = certifi.where()

        mongo_client = pymongo.MongoClient(mongo_url, **kwargs)

        if retry_attempts is None:
            retry_attempts = 3

        elif not retry_attempts:
            retry_attempts = 1

        last_exc = None
        valid = False
        t1 = time.time()
        for attempt in range(1, retry_attempts + 1):
            try:
                mongo_client.server_info()
                with mongo_client.start_session():
                    pass
                valid = True
                break

            except Exception as exc:
                last_exc = exc
                if attempt < retry_attempts:
                    cls.log.warning(
                        "Attempt {} failed. Retrying... ".format(attempt)
                    )
                    time.sleep(1)

        if not valid:
            raise last_exc

        cls.log.info("Connected to {}, delay {:.3f}s".format(
            mongo_url, time.time() - t1
        ))
        return mongo_client


# ------ Helper Mongo functions ------
# Functions can be helpful with custom tools to backup/restore mongo state.
# Not meant as API functionality that should be used in production codebase!
def get_collection_documents(database_name, collection_name, as_json=False):
    """Query all documents from a collection.

    Args:
        database_name (str): Name of database where to look for collection.
        collection_name (str): Name of collection where to look for collection.
        as_json (Optional[bool]): Output should be a json string.
            Default: 'False'

    Returns:
        Union[list[dict[str, Any]], str]: Queried documents.
    """

    client = OpenPypeMongoConnection.get_mongo_client()
    output = list(client[database_name][collection_name].find({}))
    if as_json:
        output = documents_to_json(output)
    return output


def store_collection(filepath, database_name, collection_name):
    """Store collection documents to a json file.

    Args:
        filepath (str): Path to a json file where documents will be stored.
        database_name (str): Name of database where to look for collection.
        collection_name (str): Name of collection to store.
    """

    # Make sure directory for output file exists
    dirpath = os.path.dirname(filepath)
    if not os.path.isdir(dirpath):
        os.makedirs(dirpath)

    content = get_collection_documents(database_name, collection_name, True)
    with open(filepath, "w") as stream:
        stream.write(content)


def replace_collection_documents(docs, database_name, collection_name):
    """Replace all documents in a collection with passed documents.

    Warnings:
        All existing documents in collection will be removed if there are any.

    Args:
        docs (list[dict[str, Any]]): New documents.
        database_name (str): Name of database where to look for collection.
        collection_name (str): Name of collection where new documents are
            uploaded.
    """

    client = OpenPypeMongoConnection.get_mongo_client()
    database = client[database_name]
    if collection_name in database.list_collection_names():
        database.drop_collection(collection_name)
    col = database[collection_name]
    col.insert_many(docs)


def restore_collection(filepath, database_name, collection_name):
    """Restore/replace collection from a json filepath.

    Warnings:
        All existing documents in collection will be removed if there are any.

    Args:
        filepath (str): Path to a json with documents.
        database_name (str): Name of database where to look for collection.
        collection_name (str): Name of collection where new documents are
            uploaded.
    """

    docs = load_json_file(filepath)
    replace_collection_documents(docs, database_name, collection_name)


def get_project_database(database_name=None):
    """Database object where project collections are.

    Args:
        database_name (Optional[str]): Custom name of database.

    Returns:
        pymongo.database.Database: Collection related to passed project.
    """

    if not database_name:
        database_name = get_project_database_name()
    return OpenPypeMongoConnection.get_mongo_client()[database_name]


def get_project_connection(project_name, database_name=None):
    """Direct access to mongo collection.

    We're trying to avoid using direct access to mongo. This should be used
    only for Create, Update and Remove operations until there are implemented
    api calls for that.

    Args:
        project_name (str): Project name for which collection should be
            returned.
        database_name (Optional[str]): Custom name of database.

    Returns:
        pymongo.collection.Collection: Collection related to passed project.
    """

    if not project_name:
        raise ValueError("Invalid project name {}".format(str(project_name)))
    return get_project_database(database_name)[project_name]


def get_project_documents(project_name, database_name=None):
    """Query all documents from project collection.

    Args:
        project_name (str): Name of project.
        database_name (Optional[str]): Name of mongo database where to look for
            project.

    Returns:
        list[dict[str, Any]]: Documents in project collection.
    """

    if not database_name:
        database_name = get_project_database_name()
    return get_collection_documents(database_name, project_name)


def store_project_documents(project_name, filepath, database_name=None):
    """Store project documents to a file as json string.

    Args:
        project_name (str): Name of project to store.
        filepath (str): Path to a json file where output will be stored.
        database_name (Optional[str]): Name of mongo database where to look for
            project.
    """

    if not database_name:
        database_name = get_project_database_name()

    store_collection(filepath, database_name, project_name)


def replace_project_documents(project_name, docs, database_name=None):
    """Replace documents in mongo with passed documents.

    Warnings:
        Existing project collection is removed if exists in mongo.

    Args:
        project_name (str): Name of project.
        docs (list[dict[str, Any]]): Documents to restore.
        database_name (Optional[str]): Name of mongo database where project
            collection will be created.
    """

    if not database_name:
        database_name = get_project_database_name()
    replace_collection_documents(docs, database_name, project_name)


def restore_project_documents(project_name, filepath, database_name=None):
    """Replace documents in mongo with passed documents.

    Warnings:
        Existing project collection is removed if exists in mongo.

    Args:
        project_name (str): Name of project.
        filepath (str): File to json file with project documents.
        database_name (Optional[str]): Name of mongo database where project
            collection will be created.
    """

    if not database_name:
        database_name = get_project_database_name()
    restore_collection(filepath, database_name, project_name)
