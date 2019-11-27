import logging
import os
import atexit
import tempfile
import threading
import requests

import ftrack_api
import ftrack_api.session
import ftrack_api.cache
import ftrack_api.operation
import ftrack_api._centralized_storage_scenario
import ftrack_api.event
from ftrack_api.logging import LazyLogMessage as L


class StorerEventHub(ftrack_api.event.hub.EventHub):
    def __init__(self, *args, **kwargs):
        self.sock = kwargs.pop("sock")
        super(StorerEventHub, self).__init__(*args, **kwargs)

    def _handle_packet(self, code, packet_identifier, path, data):
        """Override `_handle_packet` which extend heartbeat"""
        if self._code_name_mapping[code] == "heartbeat":
            # Reply with heartbeat.
            self.sock.sendall(b"storer")
            return self._send_packet(self._code_name_mapping['heartbeat'])

        return super(StorerEventHub, self)._handle_packet(
            code, packet_identifier, path, data
        )


class StorerSession(ftrack_api.session.Session):
    '''An isolated session for interaction with an ftrack server.'''
    def __init__(
        self, server_url=None, api_key=None, api_user=None, auto_populate=True,
        plugin_paths=None, cache=None, cache_key_maker=None,
        auto_connect_event_hub=None, schema_cache_path=None,
        plugin_arguments=None, sock=None
    ):
        '''Initialise session.

        *server_url* should be the URL of the ftrack server to connect to
        including any port number. If not specified attempt to look up from
        :envvar:`FTRACK_SERVER`.

        *api_key* should be the API key to use for authentication whilst
        *api_user* should be the username of the user in ftrack to record
        operations against. If not specified, *api_key* should be retrieved
        from :envvar:`FTRACK_API_KEY` and *api_user* from
        :envvar:`FTRACK_API_USER`.

        If *auto_populate* is True (the default), then accessing entity
        attributes will cause them to be automatically fetched from the server
        if they are not already. This flag can be changed on the session
        directly at any time.

        *plugin_paths* should be a list of paths to search for plugins. If not
        specified, default to looking up :envvar:`FTRACK_EVENT_PLUGIN_PATH`.

        *cache* should be an instance of a cache that fulfils the
        :class:`ftrack_api.cache.Cache` interface and will be used as the cache
        for the session. It can also be a callable that will be called with the
        session instance as sole argument. The callable should return ``None``
        if a suitable cache could not be configured, but session instantiation
        can continue safely.

        .. note::

            The session will add the specified cache to a pre-configured layered
            cache that specifies the top level cache as a
            :class:`ftrack_api.cache.MemoryCache`. Therefore, it is unnecessary
            to construct a separate memory cache for typical behaviour. Working
            around this behaviour or removing the memory cache can lead to
            unexpected behaviour.

        *cache_key_maker* should be an instance of a key maker that fulfils the
        :class:`ftrack_api.cache.KeyMaker` interface and will be used to
        generate keys for objects being stored in the *cache*. If not specified,
        a :class:`~ftrack_api.cache.StringKeyMaker` will be used.

        If *auto_connect_event_hub* is True then embedded event hub will be
        automatically connected to the event server and allow for publishing and
        subscribing to **non-local** events. If False, then only publishing and
        subscribing to **local** events will be possible until the hub is
        manually connected using :meth:`EventHub.connect
        <ftrack_api.event.hub.EventHub.connect>`.

        .. note::

            The event hub connection is performed in a background thread to
            improve session startup time. If a registered plugin requires a
            connected event hub then it should check the event hub connection
            status explicitly. Subscribing to events does *not* require a
            connected event hub.

        Enable schema caching by setting *schema_cache_path* to a folder path.
        If not set, :envvar:`FTRACK_API_SCHEMA_CACHE_PATH` will be used to
        determine the path to store cache in. If the environment variable is
        also not specified then a temporary directory will be used. Set to
        `False` to disable schema caching entirely.

        *plugin_arguments* should be an optional mapping (dict) of keyword
        arguments to pass to plugin register functions upon discovery. If a
        discovered plugin has a signature that is incompatible with the passed
        arguments, the discovery mechanism will attempt to reduce the passed
        arguments to only those that the plugin accepts. Note that a warning
        will be logged in this case.

        '''
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
        self._event_hub = StorerEventHub(
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
