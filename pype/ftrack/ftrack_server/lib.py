import os
try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs


def ftrack_events_mongo_settings():
    host = None
    port = None
    username = None
    password = None
    collection = None
    database = None
    auth_db = ""

    if os.environ.get('FTRACK_EVENTS_MONGO_URL'):
        result = urlparse(os.environ['FTRACK_EVENTS_MONGO_URL'])

        host = result.hostname
        try:
            port = result.port
        except ValueError:
            raise RuntimeError("invalid port specified")
        username = result.username
        password = result.password
        try:
            database = result.path.lstrip("/").split("/")[0]
            collection = result.path.lstrip("/").split("/")[1]
        except IndexError:
            if not database:
                raise RuntimeError("missing database name for logging")
        try:
            auth_db = parse_qs(result.query)['authSource'][0]
        except KeyError:
            # no auth db provided, mongo will use the one we are connecting to
            pass
    else:
        host = os.environ.get('FTRACK_EVENTS_MONGO_HOST')
        port = int(os.environ.get('FTRACK_EVENTS_MONGO_PORT', "0"))
        database = os.environ.get('FTRACK_EVENTS_MONGO_DB')
        username = os.environ.get('FTRACK_EVENTS_MONGO_USER')
        password = os.environ.get('FTRACK_EVENTS_MONGO_PASSWORD')
        collection = os.environ.get('FTRACK_EVENTS_MONGO_COL')
        auth_db = os.environ.get('FTRACK_EVENTS_MONGO_AUTH_DB', 'avalon')

    return host, port, database, username, password, collection, auth_db


def get_ftrack_event_mongo_info():
    host, port, database, username, password, collection, auth_db = ftrack_events_mongo_settings()
    user_pass = ""
    if username and password:
        user_pass = "{}:{}@".format(username, password)

    socket_path = "{}:{}".format(host, port)

    dab = ""
    if database:
        dab = "/{}".format(database)

    auth = ""
    if auth_db:
        auth = "?authSource={}".format(auth_db)

    url = "mongodb://{}{}{}{}".format(user_pass, socket_path, dab, auth)

    return url, database, collection
