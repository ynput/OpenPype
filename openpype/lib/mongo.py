import os
import sys
import time
import logging
import pymongo
import certifi

if sys.version_info[0] == 2:
    from urlparse import urlparse, parse_qs
else:
    from urllib.parse import urlparse, parse_qs


class MongoEnvNotSet(Exception):
    pass


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
        if key in query and "true" in query["ssl"]:
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
