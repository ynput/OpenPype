import os
import sys
import logging
import getpass
import atexit
import tempfile
import threading
import datetime
import time
import queue
import pymongo

import requests
import ftrack_api
import ftrack_api.session
import ftrack_api.cache
import ftrack_api.operation
import ftrack_api._centralized_storage_scenario
import ftrack_api.event
from ftrack_api.logging import LazyLogMessage as L

from pype.api import (
    Logger,
    get_default_components,
    decompose_url,
    compose_url
)

from pype.modules.ftrack.lib.custom_db_connector import CustomDbConnector


TOPIC_STATUS_SERVER = "pype.event.server.status"
TOPIC_STATUS_SERVER_RESULT = "pype.event.server.status.result"


def get_ftrack_event_mongo_info():
    database_name = (
        os.environ.get("FTRACK_EVENTS_MONGO_DB") or "pype"
    )
    collection_name = (
        os.environ.get("FTRACK_EVENTS_MONGO_COL") or "ftrack_events"
    )

    mongo_url = os.environ.get("FTRACK_EVENTS_MONGO_URL")
    if mongo_url is not None:
        components = decompose_url(mongo_url)
    else:
        components = get_default_components()

    uri = compose_url(**components)

    return uri, components["port"], database_name, collection_name


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


class SocketBaseEventHub(ftrack_api.event.hub.EventHub):

    hearbeat_msg = b"hearbeat"
    heartbeat_callbacks = []

    def __init__(self, *args, **kwargs):
        self.sock = kwargs.pop("sock")
        super(SocketBaseEventHub, self).__init__(*args, **kwargs)

    def _handle_packet(self, code, packet_identifier, path, data):
        """Override `_handle_packet` which extend heartbeat"""
        code_name = self._code_name_mapping[code]
        if code_name == "heartbeat":
            # Reply with heartbeat.
            for callback in self.heartbeat_callbacks:
                callback()

            self.sock.sendall(self.hearbeat_msg)
            return self._send_packet(self._code_name_mapping["heartbeat"])

        return super(SocketBaseEventHub, self)._handle_packet(
            code, packet_identifier, path, data
        )


class StatusEventHub(SocketBaseEventHub):
    def _handle_packet(self, code, packet_identifier, path, data):
        """Override `_handle_packet` which extend heartbeat"""
        code_name = self._code_name_mapping[code]
        if code_name == "connect":
            event = ftrack_api.event.base.Event(
                topic="pype.status.started",
                data={},
                source={
                    "id": self.id,
                    "user": {"username": self._api_user}
                }
            )
            self._event_queue.put(event)

        return super(StatusEventHub, self)._handle_packet(
            code, packet_identifier, path, data
        )


class StorerEventHub(SocketBaseEventHub):

    hearbeat_msg = b"storer"

    def _handle_packet(self, code, packet_identifier, path, data):
        """Override `_handle_packet` which extend heartbeat"""
        code_name = self._code_name_mapping[code]
        if code_name == "connect":
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


class ProcessEventHub(SocketBaseEventHub):

    hearbeat_msg = b"processor"
    uri, port, database, table_name = get_ftrack_event_mongo_info()

    is_table_created = False
    pypelog = Logger().get_logger("Session Processor")

    def __init__(self, *args, **kwargs):
        self.dbcon = CustomDbConnector(
            self.uri,
            self.database,
            self.port,
            self.table_name
        )
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

                    mongo_id = event["data"].get("_event_mongo_id")
                    if mongo_id is None:
                        continue

                    self.dbcon.update_one(
                        {"_id": mongo_id},
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
        self.dbcon.delete_many({
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
                event["data"]["_event_mongo_id"] = event_data["_id"]
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

        return super()._handle_packet(code, packet_identifier, path, data)


class SocketSession(ftrack_api.session.Session):
    '''An isolated session for interaction with an ftrack server.'''
    def __init__(
        self, server_url=None, api_key=None, api_user=None, auto_populate=True,
        plugin_paths=None, cache=None, cache_key_maker=None,
        auto_connect_event_hub=None, schema_cache_path=None,
        plugin_arguments=None, sock=None, Eventhub=None
    ):
        super(ftrack_api.session.Session, self).__init__()
        self.logger = logging.getLogger(
            __name__ + '.' + self.__class__.__name__
        )
        self._closed = False

        if server_url is None:
            server_url = os.environ.get('FTRACK_SERVER')

        if not server_url:
            raise TypeError(
                'Required "server_url" not specified. Pass as argument or set '
                'in environment variable FTRACK_SERVER.'
            )

        self._server_url = server_url

        if api_key is None:
            api_key = os.environ.get(
                'FTRACK_API_KEY',
                # Backwards compatibility
                os.environ.get('FTRACK_APIKEY')
            )

        if not api_key:
            raise TypeError(
                'Required "api_key" not specified. Pass as argument or set in '
                'environment variable FTRACK_API_KEY.'
            )

        self._api_key = api_key

        if api_user is None:
            api_user = os.environ.get('FTRACK_API_USER')
            if not api_user:
                try:
                    api_user = getpass.getuser()
                except Exception:
                    pass

        if not api_user:
            raise TypeError(
                'Required "api_user" not specified. Pass as argument, set in '
                'environment variable FTRACK_API_USER or one of the standard '
                'environment variables used by Python\'s getpass module.'
            )

        self._api_user = api_user

        # Currently pending operations.
        self.recorded_operations = ftrack_api.operation.Operations()
        self.record_operations = True

        self.cache_key_maker = cache_key_maker
        if self.cache_key_maker is None:
            self.cache_key_maker = ftrack_api.cache.StringKeyMaker()

        # Enforce always having a memory cache at top level so that the same
        # in-memory instance is returned from session.
        self.cache = ftrack_api.cache.LayeredCache([
            ftrack_api.cache.MemoryCache()
        ])

        if cache is not None:
            if callable(cache):
                cache = cache(self)

            if cache is not None:
                self.cache.caches.append(cache)

        self._managed_request = None
        self._request = requests.Session()
        self._request.auth = ftrack_api.session.SessionAuthentication(
            self._api_key, self._api_user
        )

        self.auto_populate = auto_populate

        # Fetch server information and in doing so also check credentials.
        self._server_information = self._fetch_server_information()

        # Now check compatibility of server based on retrieved information.
        self.check_server_compatibility()

        # Construct event hub and load plugins.
        if Eventhub is None:
            Eventhub = ftrack_api.event.hub.EventHub
        self._event_hub = Eventhub(
            self._server_url,
            self._api_user,
            self._api_key,
            sock=sock
        )

        self._auto_connect_event_hub_thread = None
        if auto_connect_event_hub in (None, True):
            # Connect to event hub in background thread so as not to block main
            # session usage waiting for event hub connection.
            self._auto_connect_event_hub_thread = threading.Thread(
                target=self._event_hub.connect
            )
            self._auto_connect_event_hub_thread.daemon = True
            self._auto_connect_event_hub_thread.start()

        # To help with migration from auto_connect_event_hub default changing
        # from True to False.
        self._event_hub._deprecation_warning_auto_connect = (
            auto_connect_event_hub is None
        )

        # Register to auto-close session on exit.
        atexit.register(self.close)

        self._plugin_paths = plugin_paths
        if self._plugin_paths is None:
            self._plugin_paths = os.environ.get(
                'FTRACK_EVENT_PLUGIN_PATH', ''
            ).split(os.pathsep)

        self._discover_plugins(plugin_arguments=plugin_arguments)

        # TODO: Make schemas read-only and non-mutable (or at least without
        # rebuilding types)?
        if schema_cache_path is not False:
            if schema_cache_path is None:
                schema_cache_path = os.environ.get(
                    'FTRACK_API_SCHEMA_CACHE_PATH', tempfile.gettempdir()
                )

            schema_cache_path = os.path.join(
                schema_cache_path, 'ftrack_api_schema_cache.json'
            )

        self.schemas = self._load_schemas(schema_cache_path)
        self.types = self._build_entity_type_classes(self.schemas)

        ftrack_api._centralized_storage_scenario.register(self)

        self._configure_locations()
        self.event_hub.publish(
            ftrack_api.event.base.Event(
                topic='ftrack.api.session.ready',
                data=dict(
                    session=self
                )
            ),
            synchronous=True
        )
