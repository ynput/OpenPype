import os
import sys
import time
import logging
import pymongo

if sys.version_info[0] == 2:
    from urlparse import urlparse, parse_qs
else:
    from urllib.parse import urlparse, parse_qs


class MongoEnvNotSet(Exception):
    pass


def decompose_url(url):
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


def compose_url(scheme=None,
                host=None,
                username=None,
                password=None,
                port=None,
                auth_db=None):

    url = "{scheme}://"

    if username and password:
        url += "{username}:{password}@"

    url += "{host}"
    if port:
        url += ":{port}"

    if auth_db:
        url += "?authSource={auth_db}"

    return url.format(**{
        "scheme": scheme,
        "host": host,
        "username": username,
        "password": password,
        "port": port,
        "auth_db": auth_db
    })


def get_default_components():
    mongo_url = os.environ.get("OPENPYPE_MONGO")
    if mongo_url is None:
        raise MongoEnvNotSet(
            "URL for Mongo logging connection is not set."
        )
    return decompose_url(mongo_url)


def extract_port_from_url(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme is None:
        _url = "mongodb://{}".format(url)
        parsed_url = urlparse(_url)
    return parsed_url.port


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
    parsed = urlparse(mongo_uri)
    # Force validation of scheme
    if parsed.scheme not in ["mongodb", "mongodb+srv"]:
        raise pymongo.errors.InvalidURI((
            "Invalid URI scheme:"
            " URI must begin with 'mongodb://' or 'mongodb+srv://'"
        ))
    # we have mongo connection string. Let's try if we can connect.
    components = decompose_url(mongo_uri)
    mongo_args = {
        "host": compose_url(**components),
        "serverSelectionTimeoutMS": 1000
    }
    port = components.get("port")
    if port is not None:
        mongo_args["port"] = int(port)

    # Create connection
    client = pymongo.MongoClient(**mongo_args)
    client.server_info()
    client.close()


class PypeMongoConnection:
    """Singleton MongoDB connection.

    Keeps MongoDB connections by url.
    """
    mongo_clients = {}
    log = logging.getLogger("PypeMongoConnection")

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
            except Exception:
                connection = None

        if not connection:
            cls.log.debug("Creating mongo connection to {}".format(mongo_url))
            connection = cls.create_connection(mongo_url)
            cls.mongo_clients[mongo_url] = connection

        return connection

    @classmethod
    def create_connection(cls, mongo_url, timeout=None):
        if timeout is None:
            timeout = int(os.environ.get("AVALON_TIMEOUT") or 1000)

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
