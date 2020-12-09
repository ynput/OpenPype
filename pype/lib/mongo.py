import os

try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs


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
    mongo_url = os.environ.get("AVALON_MONGO")
    if mongo_url is None:
        raise MongoEnvNotSet(
            "URL for Mongo logging connection is not set."
        )
    return decompose_url(mongo_url)
