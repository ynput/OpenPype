import os
import requests
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
    host, port, database, username, password, collection, auth_db = (
        ftrack_events_mongo_settings()
    )
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


def check_ftrack_url(url, log_errors=True):
    """Checks if Ftrack server is responding"""
    if not url:
        print('ERROR: Ftrack URL is not set!')
        return None

    url = url.strip('/ ')

    if 'http' not in url:
        if url.endswith('ftrackapp.com'):
            url = 'https://' + url
        else:
            url = 'https://{0}.ftrackapp.com'.format(url)
    try:
        result = requests.get(url, allow_redirects=False)
    except requests.exceptions.RequestException:
        if log_errors:
            print('ERROR: Entered Ftrack URL is not accesible!')
        return False

    if (result.status_code != 200 or 'FTRACK_VERSION' not in result.headers):
        if log_errors:
            print('ERROR: Entered Ftrack URL is not accesible!')
        return False

    print('DEBUG: Ftrack server {} is accessible.'.format(url))

    return url


class StorerEventHub(ftrack_api.event.hub.EventHub):
    def __init__(self, *args, **kwargs):
        self.sock = kwargs.pop("sock")
        super(StorerEventHub, self).__init__(*args, **kwargs)

    def _handle_packet(self, code, packet_identifier, path, data):
        """Override `_handle_packet` which extend heartbeat"""
        code_name = self._code_name_mapping[code]
        if code_name == "heartbeat":
            # Reply with heartbeat.
            self.sock.sendall(b"storer")
            return self._send_packet(self._code_name_mapping['heartbeat'])

        elif code_name == "connect":
            event = ftrack_api.event.base.Event(
                topic="pype.storer.started",
                data={},
                source={
                    "id": self.id,
                    "user": {"username": self._api_user}
                }
            )
            self._event_queue.put(event)

        return super(StorerEventHub, self)._handle_packet(
            code, packet_identifier, path, data
        )


class ProcessEventHub(ftrack_api.event.hub.EventHub):
    url, database, table_name = get_ftrack_event_mongo_info()

    is_table_created = False
    pypelog = Logger().get_logger("Session Processor")

    def __init__(self, *args, **kwargs):
        self.dbcon = DbConnector(
            mongo_url=self.url,
            database_name=self.database,
            table_name=self.table_name
        )
        self.sock = kwargs.pop("sock")
        super(ProcessEventHub, self).__init__(*args, **kwargs)

    def prepare_dbcon(self):
        try:
            self.dbcon.install()
            self.dbcon._database.list_collection_names()
        except pymongo.errors.AutoReconnect:
            self.pypelog.error(
                "Mongo server \"{}\" is not responding, exiting.".format(
                    os.environ["AVALON_MONGO"]
                )
            )
            sys.exit(0)

        except pymongo.errors.OperationFailure:
            self.pypelog.error((
                "Error with Mongo access, probably permissions."
                "Check if exist database with name \"{}\""
                " and collection \"{}\" inside."
            ).format(self.database, self.table_name))
            self.sock.sendall(b"MongoError")
            sys.exit(0)

    def wait(self, duration=None):
        """Overriden wait

        Event are loaded from Mongo DB when queue is empty. Handled event is
        set as processed in Mongo DB.
        """
        started = time.time()
        self.prepare_dbcon()
        while True:
            try:
                event = self._event_queue.get(timeout=0.1)
            except queue.Empty:
                if not self.load_events():
                    time.sleep(0.5)
            else:
                try:
                    self._handle(event)
                    self.dbcon.update_one(
                        {"id": event["id"]},
                        {"$set": {"pype_data.is_processed": True}}
                    )
                except pymongo.errors.AutoReconnect:
                    self.pypelog.error((
                        "Mongo server \"{}\" is not responding, exiting."
                    ).format(os.environ["AVALON_MONGO"]))
                    sys.exit(0)
                # Additional special processing of events.
                if event['topic'] == 'ftrack.meta.disconnected':
                    break

            if duration is not None:
                if (time.time() - started) > duration:
                    break

    def load_events(self):
        """Load not processed events sorted by stored date"""
        ago_date = datetime.datetime.now() - datetime.timedelta(days=3)
        result = self.dbcon.delete_many({
            "pype_data.stored": {"$lte": ago_date},
            "pype_data.is_processed": True
        })

        not_processed_events = self.dbcon.find(
            {"pype_data.is_processed": False}
        ).sort(
            [("pype_data.stored", pymongo.ASCENDING)]
        )

        found = False
        for event_data in not_processed_events:
            new_event_data = {
                k: v for k, v in event_data.items()
                if k not in ["_id", "pype_data"]
            }
            try:
                event = ftrack_api.event.base.Event(**new_event_data)
            except Exception:
                self.logger.exception(L(
                    'Failed to convert payload into event: {0}',
                    event_data
                ))
                continue
            found = True
            self._event_queue.put(event)

        return found

    def _handle_packet(self, code, packet_identifier, path, data):
        """Override `_handle_packet` which skip events and extend heartbeat"""
        code_name = self._code_name_mapping[code]
        if code_name == "event":
            return
        if code_name == "heartbeat":
            self.sock.sendall(b"processor")
            return self._send_packet(self._code_name_mapping["heartbeat"])

        return super()._handle_packet(code, packet_identifier, path, data)
