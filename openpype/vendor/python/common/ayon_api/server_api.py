import os
import re
import io
import json
import time
import logging
import collections
import platform
import copy
import uuid
import warnings
from contextlib import contextmanager

import six

try:
    from http import HTTPStatus
except ImportError:
    HTTPStatus = None

import requests
try:
    # This should be used if 'requests' have it available
    from requests.exceptions import JSONDecodeError as RequestsJSONDecodeError
except ImportError:
    # Older versions of 'requests' don't have custom exception for json
    #   decode error
    try:
        from simplejson import JSONDecodeError as RequestsJSONDecodeError
    except ImportError:
        from json import JSONDecodeError as RequestsJSONDecodeError

from .constants import (
    SERVER_RETRIES_ENV_KEY,
    DEFAULT_PRODUCT_TYPE_FIELDS,
    DEFAULT_PROJECT_FIELDS,
    DEFAULT_FOLDER_FIELDS,
    DEFAULT_TASK_FIELDS,
    DEFAULT_PRODUCT_FIELDS,
    DEFAULT_VERSION_FIELDS,
    DEFAULT_REPRESENTATION_FIELDS,
    REPRESENTATION_FILES_FIELDS,
    DEFAULT_WORKFILE_INFO_FIELDS,
    DEFAULT_EVENT_FIELDS,
    DEFAULT_USER_FIELDS,
)
from .graphql import GraphQlQuery, INTROSPECTION_QUERY
from .graphql_queries import (
    project_graphql_query,
    projects_graphql_query,
    project_product_types_query,
    product_types_query,
    folders_graphql_query,
    tasks_graphql_query,
    products_graphql_query,
    versions_graphql_query,
    representations_graphql_query,
    representations_parents_qraphql_query,
    workfiles_info_graphql_query,
    events_graphql_query,
    users_graphql_query,
)
from .exceptions import (
    FailedOperations,
    UnauthorizedError,
    AuthenticationError,
    ServerNotReached,
    ServerError,
    HTTPRequestError,
)
from .utils import (
    RepresentationParents,
    prepare_query_string,
    logout_from_server,
    create_entity_id,
    entity_data_json_default,
    failed_json_default,
    TransferProgress,
    create_dependency_package_basename,
    ThumbnailContent,
    get_default_timeout,
    get_default_settings_variant,
    get_default_site_id,
)

_PLACEHOLDER = object()
PatternType = type(re.compile(""))
JSONDecodeError = getattr(json, "JSONDecodeError", ValueError)
# This should be collected from server schema
PROJECT_NAME_ALLOWED_SYMBOLS = "a-zA-Z0-9_"
PROJECT_NAME_REGEX = re.compile(
    "^[{}]+$".format(PROJECT_NAME_ALLOWED_SYMBOLS)
)

VERSION_REGEX = re.compile(
    r"(?P<major>0|[1-9]\d*)"
    r"\.(?P<minor>0|[1-9]\d*)"
    r"\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[a-zA-Z\d\-.]*))?"
    r"(?:\+(?P<buildmetadata>[a-zA-Z\d\-.]*))?"
)


def _get_description(response):
    if HTTPStatus is None:
        return str(response.orig_response)
    return HTTPStatus(response.status).description


class RequestType:
    def __init__(self, name):
        self.name = name

    def __hash__(self):
        return self.name.__hash__()


class RequestTypes:
    get = RequestType("GET")
    post = RequestType("POST")
    put = RequestType("PUT")
    patch = RequestType("PATCH")
    delete = RequestType("DELETE")


class RestApiResponse(object):
    """API Response."""

    def __init__(self, response, data=None):
        if response is None:
            status_code = 500
        else:
            status_code = response.status_code
        self._response = response
        self.status = status_code
        self._data = data

    @property
    def text(self):
        if self._response is None:
            return self.detail
        return self._response.text

    @property
    def orig_response(self):
        return self._response

    @property
    def headers(self):
        if self._response is None:
            return {}
        return self._response.headers

    @property
    def data(self):
        if self._data is None:
            try:
                self._data = self.orig_response.json()
            except RequestsJSONDecodeError:
                self._data = {}
        return self._data

    @property
    def content(self):
        if self._response is None:
            return b""
        return self._response.content

    @property
    def content_type(self):
        return self.headers.get("Content-Type")

    @property
    def detail(self):
        detail = self.get("detail")
        if detail:
            return detail
        return _get_description(self)

    @property
    def status_code(self):
        return self.status

    def raise_for_status(self, message=None):
        if self._response is None:
            if self._data and self._data.get("detail"):
                raise ServerError(self._data["detail"])
            raise ValueError("Response is not available.")

        try:
            self._response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            if message is None:
                message = str(exc)
            raise HTTPRequestError(message, exc.response)

    def __enter__(self, *args, **kwargs):
        return self._response.__enter__(*args, **kwargs)

    def __contains__(self, key):
        return key in self.data

    def __repr__(self):
        return "<{} [{}]>".format(self.__class__.__name__, self.status)

    def __len__(self):
        return 200 <= self.status < 400

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        data = self.data
        if isinstance(data, dict):
            return self.data.get(key, default)
        return default


class GraphQlResponse:
    def __init__(self, data):
        self.data = data
        self.errors = data.get("errors")

    def __len__(self):
        if self.errors:
            return 0
        return 1

    def __repr__(self):
        if self.errors:
            return "<{} errors={}>".format(
                self.__class__.__name__, self.errors[0]['message']
            )
        return "<{}>".format(self.__class__.__name__)


def fill_own_attribs(entity):
    if not entity or not entity.get("attrib"):
        return

    attributes = set(entity["ownAttrib"])

    own_attrib = {}
    entity["ownAttrib"] = own_attrib

    for key, value in entity["attrib"].items():
        if key not in attributes:
            own_attrib[key] = None
        else:
            own_attrib[key] = copy.deepcopy(value)


class _AsUserStack:
    """Handle stack of users used over server api connection in service mode.

    ServerAPI can behave as other users if it is using special API key.

    Examples:
        >>> stack = _AsUserStack()
        >>> stack.set_default_username("DefaultName")
        >>> print(stack.username)
        DefaultName
        >>> with stack.as_user("Other1"):
        ...     print(stack.username)
        ...     with stack.as_user("Other2"):
        ...         print(stack.username)
        ...     print(stack.username)
        ...     stack.clear()
        ...     print(stack.username)
        Other1
        Other2
        Other1
        None
        >>> print(stack.username)
        None
        >>> stack.set_default_username("DefaultName")
        >>> print(stack.username)
        DefaultName
    """

    def __init__(self):
        self._users_by_id = {}
        self._user_ids = []
        self._last_user = None
        self._default_user = None

    def clear(self):
        self._users_by_id = {}
        self._user_ids = []
        self._last_user = None
        self._default_user = None

    @property
    def username(self):
        # Use '_user_ids' for boolean check to have ability "unset"
        #   default user
        if self._user_ids:
            return self._last_user
        return self._default_user

    def get_default_username(self):
        return self._default_user

    def set_default_username(self, username=None):
        self._default_user = username

    default_username = property(get_default_username, set_default_username)

    @contextmanager
    def as_user(self, username):
        self._last_user = username
        user_id = uuid.uuid4().hex
        self._user_ids.append(user_id)
        self._users_by_id[user_id] = username
        try:
            yield
        finally:
            self._users_by_id.pop(user_id, None)
            if not self._user_ids:
                return

            # First check if is the user id the last one
            was_last = self._user_ids[-1] == user_id
            # Remove id from variables
            if user_id in self._user_ids:
                self._user_ids.remove(user_id)

            if not was_last:
                return

            new_last_user = None
            if self._user_ids:
                new_last_user = self._users_by_id.get(self._user_ids[-1])
            self._last_user = new_last_user


class ServerAPI(object):
    """Base handler of connection to server.

    Requires url to server which is used as base for api and graphql calls.

    Login cause that a session is used

    Args:
        base_url (str): Example: http://localhost:5000
        token (Optional[str]): Access token (api key) to server.
        site_id (Optional[str]): Unique name of site. Should be the same when
            connection is created from the same machine under same user.
        client_version (Optional[str]): Version of client application (used in
            desktop client application).
        default_settings_variant (Optional[Literal["production", "staging"]]):
            Settings variant used by default if a method for settings won't
            get any (by default is 'production').
        sender (Optional[str]): Sender of requests. Used in server logs and
            propagated into events.
        ssl_verify (Union[bool, str, None]): Verify SSL certificate
            Looks for env variable value 'AYON_CA_FILE' by default. If not
            available then 'True' is used.
        cert (Optional[str]): Path to certificate file. Looks for env
            variable value 'AYON_CERT_FILE' by default.
        create_session (Optional[bool]): Create session for connection if
            token is available. Default is True.
        timeout (Optional[float]): Timeout for requests.
        max_retries (Optional[int]): Number of retries for requests.
    """
    _default_max_retries = 3
    # 1 MB chunk by default
    # TODO find out if these are reasonable default value
    default_download_chunk_size = 1024 * 1024
    default_upload_chunk_size = 1024 * 1024

    def __init__(
        self,
        base_url,
        token=None,
        site_id=_PLACEHOLDER,
        client_version=None,
        default_settings_variant=None,
        sender=None,
        ssl_verify=None,
        cert=None,
        create_session=True,
        timeout=None,
        max_retries=None,
    ):
        if not base_url:
            raise ValueError("Invalid server URL {}".format(str(base_url)))

        base_url = base_url.rstrip("/")
        self._base_url = base_url
        self._rest_url = "{}/api".format(base_url)
        self._graphql_url = "{}/graphql".format(base_url)
        self._log = None
        self._access_token = token
        # Allow to have 'site_id' to 'None'
        if site_id is _PLACEHOLDER:
            site_id = get_default_site_id()
        self._site_id = site_id
        self._client_version = client_version
        self._default_settings_variant = (
            default_settings_variant
            or get_default_settings_variant()
        )
        self._sender = sender

        self._timeout = None
        self._max_retries = None

        # Set timeout and max retries based on passed values
        self.set_timeout(timeout)
        self.set_max_retries(max_retries)

        if ssl_verify is None:
            # Custom AYON env variable for CA file or 'True'
            # - that should cover most default behaviors in 'requests'
            #   with 'certifi'
            ssl_verify = os.environ.get("AYON_CA_FILE") or True

        if cert is None:
            cert = os.environ.get("AYON_CERT_FILE")

        self._ssl_verify = ssl_verify
        self._cert = cert

        self._access_token_is_service = None
        self._token_is_valid = None
        self._token_validation_started = False
        self._server_available = None
        self._server_version = None
        self._server_version_tuple = None

        self._graphql_allows_data_in_query = None

        self._session = None

        self._base_functions_mapping = {
            RequestTypes.get: requests.get,
            RequestTypes.post: requests.post,
            RequestTypes.put: requests.put,
            RequestTypes.patch: requests.patch,
            RequestTypes.delete: requests.delete
        }
        self._session_functions_mapping = {}

        # Attributes cache
        self._attributes_schema = None
        self._entity_type_attributes_cache = {}

        self._as_user_stack = _AsUserStack()

        # Create session
        if self._access_token and create_session:
            self.validate_server_availability()
            self.create_session()

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    def get_base_url(self):
        return self._base_url

    def get_rest_url(self):
        return self._rest_url

    base_url = property(get_base_url)
    rest_url = property(get_rest_url)

    def get_ssl_verify(self):
        """Enable ssl verification.

        Returns:
            bool: Current state of ssl verification.
        """

        return self._ssl_verify

    def set_ssl_verify(self, ssl_verify):
        """Change ssl verification state.

        Args:
            ssl_verify (Union[bool, str, None]): Enabled/disable
                ssl verification, can be a path to file.
        """

        if self._ssl_verify == ssl_verify:
            return
        self._ssl_verify = ssl_verify
        if self._session is not None:
            self._session.verify = ssl_verify

    def get_cert(self):
        """Current cert file used for connection to server.

        Returns:
            Union[str, None]: Path to cert file.
        """

        return self._cert

    def set_cert(self, cert):
        """Change cert file used for connection to server.

        Args:
            cert (Union[str, None]): Path to cert file.
        """

        if cert == self._cert:
            return
        self._cert = cert
        if self._session is not None:
            self._session.cert = cert

    ssl_verify = property(get_ssl_verify, set_ssl_verify)
    cert = property(get_cert, set_cert)

    @classmethod
    def get_default_timeout(cls):
        """Default value for requests timeout.

        Utils function 'get_default_timeout' is used by default.

        Returns:
            float: Timeout value in seconds.
        """

        return get_default_timeout()

    @classmethod
    def get_default_max_retries(cls):
        """Default value for requests max retries.

        First looks for environment variable SERVER_RETRIES_ENV_KEY, which
        can affect max retries value. If not available then use class
        attribute '_default_max_retries'.

        Returns:
            int: Max retries value.
        """

        try:
            return int(os.environ.get(SERVER_RETRIES_ENV_KEY))
        except (ValueError, TypeError):
            pass

        return cls._default_max_retries

    def get_timeout(self):
        """Current value for requests timeout.

        Returns:
            float: Timeout value in seconds.
        """

        return self._timeout

    def set_timeout(self, timeout):
        """Change timeout value for requests.

        Args:
            timeout (Union[float, None]): Timeout value in seconds.
        """

        if timeout is None:
            timeout = self.get_default_timeout()
        self._timeout = float(timeout)

    def get_max_retries(self):
        """Current value for requests max retries.

        Returns:
            int: Max retries value.
        """

        return self._max_retries

    def set_max_retries(self, max_retries):
        """Change max retries value for requests.

        Args:
            max_retries (Union[int, None]): Max retries value.
        """

        if max_retries is None:
            max_retries = self.get_default_max_retries()
        self._max_retries = int(max_retries)

    timeout = property(get_timeout, set_timeout)
    max_retries = property(get_max_retries, set_max_retries)

    @property
    def access_token(self):
        """Access token used for authorization to server.

        Returns:
            Union[str, None]: Token string or None if not authorized yet.
        """

        return self._access_token

    def get_site_id(self):
        """Site id used for connection.

        Site id tells server from which machine/site is connection created and
        is used for default site overrides when settings are received.

        Returns:
            Union[str, None]: Site id value or None if not filled.
        """

        return self._site_id

    def set_site_id(self, site_id):
        """Change site id of connection.

        Behave as specific site for server. It affects default behavior of
        settings getter methods.

        Args:
            site_id (Union[str, None]): Site id value, or 'None' to unset.
        """

        if self._site_id == site_id:
            return
        self._site_id = site_id
        # Recreate session on machine id change
        self._update_session_headers()

    site_id = property(get_site_id, set_site_id)

    def get_client_version(self):
        """Version of client used to connect to server.

        Client version is AYON client build desktop application.

        Returns:
            str: Client version string used in connection.
        """

        return self._client_version

    def set_client_version(self, client_version):
        """Set version of client used to connect to server.

        Client version is AYON client build desktop application.

        Args:
            client_version (Union[str, None]): Client version string.
        """

        if self._client_version == client_version:
            return

        self._client_version = client_version
        self._update_session_headers()

    client_version = property(get_client_version, set_client_version)

    def get_default_settings_variant(self):
        """Default variant used for settings.

        Returns:
            Union[str, None]: name of variant or None.
        """

        return self._default_settings_variant

    def set_default_settings_variant(self, variant):
        """Change default variant for addon settings.

        Note:
            It is recommended to set only 'production' or 'staging' variants
                as default variant.

        Args:
            variant (str): Settings variant name. It is possible to use
                'production', 'staging' or name of dev bundle.
        """

        self._default_settings_variant = variant

    default_settings_variant = property(
        get_default_settings_variant,
        set_default_settings_variant
    )

    def get_sender(self):
        """Sender used to send requests.

        Returns:
            Union[str, None]: Sender name or None.
        """

        return self._sender

    def set_sender(self, sender):
        """Change sender used for requests.

        Args:
            sender (Union[str, None]): Sender name or None.
        """

        if sender == self._sender:
            return
        self._sender = sender
        self._update_session_headers()

    sender = property(get_sender, set_sender)

    def get_default_service_username(self):
        """Default username used for callbacks when used with service API key.

        Returns:
            Union[str, None]: Username if any was filled.
        """

        return self._as_user_stack.get_default_username()

    def set_default_service_username(self, username=None):
        """Service API will work as other user.

        Service API keys can work as other user. It can be temporary using
        context manager 'as_user' or it is possible to set default username if
        'as_user' context manager is not entered.

        Args:
            username (Optional[str]): Username to work as when service.

        Raises:
            ValueError: When connection is not yet authenticated or api key
                is not service token.
        """

        current_username = self._as_user_stack.get_default_username()
        if current_username == username:
            return

        if not self.has_valid_token:
            raise ValueError(
                "Authentication of connection did not happen yet."
            )

        if not self._access_token_is_service:
            raise ValueError(
                "Can't set service username. API key is not a service token."
            )

        self._as_user_stack.set_default_username(username)
        if self._as_user_stack.username == username:
            self._update_session_headers()

    @contextmanager
    def as_username(self, username):
        """Service API will temporarily work as other user.

        This method can be used only if service API key is logged in.

        Args:
            username (Union[str, None]): Username to work as when service.

        Raises:
            ValueError: When connection is not yet authenticated or api key
                is not service token.
        """

        if not self.has_valid_token:
            raise ValueError(
                "Authentication of connection did not happen yet."
            )

        if not self._access_token_is_service:
            raise ValueError(
                "Can't set service username. API key is not a service token."
            )

        with self._as_user_stack.as_user(username) as o:
            self._update_session_headers()
            try:
                yield o
            finally:
                self._update_session_headers()

    @property
    def is_server_available(self):
        if self._server_available is None:
            response = requests.get(
                self._base_url,
                cert=self._cert,
                verify=self._ssl_verify
            )
            self._server_available = response.status_code == 200
        return self._server_available

    @property
    def has_valid_token(self):
        if self._access_token is None:
            return False

        if self._token_is_valid is None:
            self.validate_token()
        return self._token_is_valid

    def validate_server_availability(self):
        if not self.is_server_available:
            raise ServerNotReached("Server \"{}\" can't be reached".format(
                self._base_url
            ))

    def validate_token(self):
        try:
            self._token_validation_started = True
            # TODO add other possible validations
            # - existence of 'user' key in info
            # - validate that 'site_id' is in 'sites' in info
            self.get_info()
            self.get_user()
            self._token_is_valid = True

        except UnauthorizedError:
            self._token_is_valid = False

        finally:
            self._token_validation_started = False
        return self._token_is_valid

    def set_token(self, token):
        self.reset_token()
        self._access_token = token
        self.get_user()

    def reset_token(self):
        self._access_token = None
        self._token_is_valid = None
        self.close_session()

    def create_session(self, ignore_existing=True, force=False):
        """Create a connection session.

        Session helps to keep connection with server without
            need to reconnect on each call.

        Args:
            ignore_existing (bool): If session already exists,
                ignore creation.
            force (bool): If session already exists, close it and
                create new.
        """

        if force and self._session is not None:
            self.close_session()

        if self._session is not None:
            if ignore_existing:
                return
            raise ValueError("Session is already created.")

        self._as_user_stack.clear()
        # Validate token before session creation
        self.validate_token()

        session = requests.Session()
        session.cert = self._cert
        session.verify = self._ssl_verify
        session.headers.update(self.get_headers())

        self._session_functions_mapping = {
            RequestTypes.get: session.get,
            RequestTypes.post: session.post,
            RequestTypes.put: session.put,
            RequestTypes.patch: session.patch,
            RequestTypes.delete: session.delete
        }
        self._session = session

    def close_session(self):
        if self._session is None:
            return

        session = self._session
        self._session = None
        self._session_functions_mapping = {}
        session.close()

    def _update_session_headers(self):
        if self._session is None:
            return

        # Header keys that may change over time
        for key, value in (
            ("X-as-user", self._as_user_stack.username),
            ("x-ayon-version", self._client_version),
            ("x-ayon-site-id", self._site_id),
            ("x-sender", self._sender),
        ):
            if value is not None:
                self._session.headers[key] = value
            elif key in self._session.headers:
                self._session.headers.pop(key)

    def get_info(self):
        """Get information about current used api key.

        By default, the 'info' contains only 'uptime' and 'version'. With
        logged user info also contains information about user and machines on
        which was logged in.

        Todos:
            Use this method for validation of token instead of 'get_user'.

        Returns:
            dict[str, Any]: Information from server.
        """

        response = self.get("info")
        return response.data

    def get_server_version(self):
        """Get server version.

        Version should match semantic version (https://semver.org/).

        Returns:
            str: Server version.
        """

        if self._server_version is None:
            self._server_version = self.get_info()["version"]
        return self._server_version

    def get_server_version_tuple(self):
        """Get server version as tuple.

        Version should match semantic version (https://semver.org/).

        This function only returns first three numbers of version.

        Returns:
            Tuple[int, int, int, Union[str, None], Union[str, None]]: Server
                version.
        """

        if self._server_version_tuple is None:
            re_match = VERSION_REGEX.fullmatch(
                self.get_server_version())
            self._server_version_tuple = (
                int(re_match.group("major")),
                int(re_match.group("minor")),
                int(re_match.group("patch")),
                re_match.group("prerelease") or "",
                re_match.group("buildmetadata") or "",
            )
        return self._server_version_tuple

    server_version = property(get_server_version)
    server_version_tuple = property(get_server_version_tuple)

    @property
    def graphql_allows_data_in_query(self):
        """GraphlQl query can support 'data' field.

        This applies only to project hierarchy entities 'project', 'folder',
        'task', 'product', 'version' and 'representation'. Others like 'user'
        still require to use rest api to access 'data'.

        Returns:
            bool: True if server supports 'data' field in GraphQl query.
        """

        if self._graphql_allows_data_in_query is None:
            major, minor, patch, _, _ = self.server_version_tuple
            graphql_allows_data_in_query = True
            if (major, minor, patch) < (0, 5, 5):
                graphql_allows_data_in_query = False
            self._graphql_allows_data_in_query = graphql_allows_data_in_query
        return self._graphql_allows_data_in_query

    def _get_user_info(self):
        if self._access_token is None:
            return None

        if self._access_token_is_service is not None:
            response = self.get("users/me")
            return response.data

        self._access_token_is_service = False
        response = self.get("users/me")
        if response.status == 200:
            return response.data

        self._access_token_is_service = True
        response = self.get("users/me")
        if response.status == 200:
            return response.data

        self._access_token_is_service = None
        return None

    def get_users(self, usernames=None, fields=None):
        """Get Users.

        Args:
            usernames (Optional[Iterable[str]]): Filter by usernames.
            fields (Optional[Iterable[str]]): fields to be queried
                for users.

        Returns:
            Generator[dict[str, Any]]: Queried users.
        """

        filters = {}
        if usernames is not None:
            usernames = set(usernames)
            if not usernames:
                return
            filters["userNames"] = list(usernames)

        if not fields:
            fields = self.get_default_fields_for_type("user")

        query = users_graphql_query(set(fields))
        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        for parsed_data in query.continuous_query(self):
            for user in parsed_data["users"]:
                user["accessGroups"] = json.loads(
                    user["accessGroups"])
                yield user

    def get_user(self, username=None):
        output = None
        if username is None:
            output = self._get_user_info()
        else:
            response = self.get("users/{}".format(username))
            if response.status == 200:
                output = response.data

        if output is None:
            raise UnauthorizedError("User is not authorized.")
        return output

    def get_headers(self, content_type=None):
        if content_type is None:
            content_type = "application/json"

        headers = {
            "Content-Type": content_type,
            "x-ayon-platform": platform.system().lower(),
            "x-ayon-hostname": platform.node(),
        }
        if self._site_id is not None:
            headers["x-ayon-site-id"] = self._site_id

        if self._client_version is not None:
            headers["x-ayon-version"] = self._client_version

        if self._sender is not None:
            headers["x-sender"] = self._sender

        if self._access_token:
            if self._access_token_is_service:
                headers["X-Api-Key"] = self._access_token
                username = self._as_user_stack.username
                if username:
                    headers["X-as-user"] = username
            else:
                headers["Authorization"] = "Bearer {}".format(
                    self._access_token)
        return headers

    def login(self, username, password, create_session=True):
        """Login to server.

        Args:
            username (str): Username.
            password (str): Password.
            create_session (Optional[bool]): Create session after login.
                Default: True.

        Raises:
            AuthenticationError: Login failed.
        """

        if self.has_valid_token:
            try:
                user_info = self.get_user()
            except UnauthorizedError:
                user_info = {}

            current_username = user_info.get("name")
            if current_username == username:
                self.close_session()
                if create_session:
                    self.create_session()
                return

        self.reset_token()

        self.validate_server_availability()

        self._token_validation_started = True

        try:
            response = self.post(
                "auth/login",
                name=username,
                password=password
            )
            if response.status_code != 200:
                _detail = response.data.get("detail")
                details = ""
                if _detail:
                    details = " {}".format(_detail)

                raise AuthenticationError("Login failed {}".format(details))

        finally:
            self._token_validation_started = False

        self._access_token = response["token"]

        if not self.has_valid_token:
            raise AuthenticationError("Invalid credentials")

        if create_session:
            self.create_session()

    def logout(self, soft=False):
        if self._access_token:
            if not soft:
                self._logout()
            self.reset_token()

    def _logout(self):
        logout_from_server(self._base_url, self._access_token)

    def _do_rest_request(self, function, url, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        max_retries = kwargs.get("max_retries", self.max_retries)
        if max_retries < 1:
            max_retries = 1
        if self._session is None:
            # Validate token if was not yet validated
            #    - ignore validation if we're in middle of
            #       validation
            if (
                self._token_is_valid is None
                and not self._token_validation_started
            ):
                self.validate_token()

            if "headers" not in kwargs:
                kwargs["headers"] = self.get_headers()

            if isinstance(function, RequestType):
                function = self._base_functions_mapping[function]

        elif isinstance(function, RequestType):
            function = self._session_functions_mapping[function]

        response = None
        new_response = None
        for retry_idx in reversed(range(max_retries)):
            try:
                response = function(url, **kwargs)
                break

            except ConnectionRefusedError:
                if retry_idx == 0:
                    self.log.warning(
                        "Connection error happened.", exc_info=True
                    )

                # Server may be restarting
                new_response = RestApiResponse(
                    None,
                    {"detail": "Unable to connect the server. Connection refused"}
                )

            except requests.exceptions.Timeout:
                # Connection timed out
                new_response = RestApiResponse(
                    None,
                    {"detail": "Connection timed out."}
                )

            except requests.exceptions.ConnectionError:
                # Log warning only on last attempt
                if retry_idx == 0:
                    self.log.warning(
                        "Connection error happened.", exc_info=True
                    )

                new_response = RestApiResponse(
                    None,
                    {"detail": "Unable to connect the server. Connection error"}
                )

            time.sleep(0.1)

        if new_response is not None:
            return new_response

        content_type = response.headers.get("Content-Type")
        if content_type == "application/json":
            try:
                new_response = RestApiResponse(response)
            except JSONDecodeError:
                new_response = RestApiResponse(
                    None,
                    {
                        "detail": "The response is not a JSON: {}".format(
                            response.text)
                    }
                )

        else:
            new_response = RestApiResponse(response)

        self.log.debug("Response {}".format(str(new_response)))
        return new_response

    def raw_post(self, entrypoint, **kwargs):
        entrypoint = entrypoint.lstrip("/").rstrip("/")
        self.log.debug("Executing [POST] {}".format(entrypoint))
        url = "{}/{}".format(self._rest_url, entrypoint)
        return self._do_rest_request(
            RequestTypes.post,
            url,
            **kwargs
        )

    def raw_put(self, entrypoint, **kwargs):
        entrypoint = entrypoint.lstrip("/").rstrip("/")
        self.log.debug("Executing [PUT] {}".format(entrypoint))
        url = "{}/{}".format(self._rest_url, entrypoint)
        return self._do_rest_request(
            RequestTypes.put,
            url,
            **kwargs
        )

    def raw_patch(self, entrypoint, **kwargs):
        entrypoint = entrypoint.lstrip("/").rstrip("/")
        self.log.debug("Executing [PATCH] {}".format(entrypoint))
        url = "{}/{}".format(self._rest_url, entrypoint)
        return self._do_rest_request(
            RequestTypes.patch,
            url,
            **kwargs
        )

    def raw_get(self, entrypoint, **kwargs):
        entrypoint = entrypoint.lstrip("/").rstrip("/")
        self.log.debug("Executing [GET] {}".format(entrypoint))
        url = "{}/{}".format(self._rest_url, entrypoint)
        return self._do_rest_request(
            RequestTypes.get,
            url,
            **kwargs
        )

    def raw_delete(self, entrypoint, **kwargs):
        entrypoint = entrypoint.lstrip("/").rstrip("/")
        self.log.debug("Executing [DELETE] {}".format(entrypoint))
        url = "{}/{}".format(self._rest_url, entrypoint)
        return self._do_rest_request(
            RequestTypes.delete,
            url,
            **kwargs
        )

    def post(self, entrypoint, **kwargs):
        return self.raw_post(entrypoint, json=kwargs)

    def put(self, entrypoint, **kwargs):
        return self.raw_put(entrypoint, json=kwargs)

    def patch(self, entrypoint, **kwargs):
        return self.raw_patch(entrypoint, json=kwargs)

    def get(self, entrypoint, **kwargs):
        return self.raw_get(entrypoint, params=kwargs)

    def delete(self, entrypoint, **kwargs):
        return self.raw_delete(entrypoint, params=kwargs)

    def get_event(self, event_id):
        """Query full event data by id.

        Events received using event server do not contain full information. To
        get the full event information is required to receive it explicitly.

        Args:
            event_id (str): Id of event.

        Returns:
            dict[str, Any]: Full event data.
        """

        response = self.get("events/{}".format(event_id))
        response.raise_for_status()
        return response.data

    def get_events(
        self,
        topics=None,
        project_names=None,
        states=None,
        users=None,
        include_logs=None,
        has_children=None,
        newer_than=None,
        older_than=None,
        fields=None
    ):
        """Get events from server with filtering options.

        Notes:
            Not all event happen on a project.

        Args:
            topics (Optional[Iterable[str]]): Name of topics.
            project_names (Optional[Iterable[str]]): Project on which
                event happened.
            states (Optional[Iterable[str]]): Filtering by states.
            users (Optional[Iterable[str]]): Filtering by users
                who created/triggered an event.
            include_logs (Optional[bool]): Query also log events.
            has_children (Optional[bool]): Event is with/without children
                events. If 'None' then all events are returned, default.
            newer_than (Optional[str]): Return only events newer than given
                iso datetime string.
            older_than (Optional[str]): Return only events older than given
                iso datetime string.
            fields (Optional[Iterable[str]]): Fields that should be received
                for each event.

        Returns:
            Generator[dict[str, Any]]: Available events matching filters.
        """

        filters = {}
        if topics is not None:
            topics = set(topics)
            if not topics:
                return
            filters["eventTopics"] = list(topics)

        if project_names is not None:
            project_names = set(project_names)
            if not project_names:
                return
            filters["projectNames"] = list(project_names)

        if states is not None:
            states = set(states)
            if not states:
                return
            filters["eventStates"] = list(states)

        if users is not None:
            users = set(users)
            if not users:
                return
            filters["eventUsers"] = list(users)

        if include_logs is None:
            include_logs = False
        filters["includeLogsFilter"] = include_logs

        if has_children is not None:
            filters["hasChildrenFilter"] = has_children

        if newer_than is not None:
            filters["newerThanFilter"] = newer_than

        if older_than is not None:
            filters["olderThanFilter"] = older_than

        if not fields:
            fields = self.get_default_fields_for_type("event")

        query = events_graphql_query(set(fields))
        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        for parsed_data in query.continuous_query(self):
            for event in parsed_data["events"]:
                yield event

    def update_event(
        self,
        event_id,
        sender=None,
        project_name=None,
        status=None,
        description=None,
        summary=None,
        payload=None,
        progress=None,
        retries=None
    ):
        kwargs = {
            key: value
            for key, value in (
                ("sender", sender),
                ("project", project_name),
                ("status", status),
                ("description", description),
                ("summary", summary),
                ("payload", payload),
                ("progress", progress),
                ("retries", retries),
            )
            if value is not None
        }
        # 'progress' and 'retries' are available since 0.5.x server version
        major, minor, _, _, _ = self.server_version_tuple
        if (major, minor) < (0, 5):
            args = []
            if progress is not None:
                args.append("progress")
            if retries is not None:
                args.append("retries")
            fields = ", ".join("'{}'".format(f) for f in args)
            ending = "s" if len(args) > 1 else ""
            raise ValueError((
                 "Your server version '{}' does not support update"
                 " of {} field{} on event. The fields are supported since"
                 " server version '0.5'."
            ).format(self.get_server_version(), fields, ending))

        response = self.patch(
            "events/{}".format(event_id),
            **kwargs
        )
        response.raise_for_status()

    def dispatch_event(
        self,
        topic,
        sender=None,
        event_hash=None,
        project_name=None,
        username=None,
        dependencies=None,
        description=None,
        summary=None,
        payload=None,
        finished=True,
        store=True,
    ):
        """Dispatch event to server.

        Arg:
            topic (str): Event topic used for filtering of listeners.
            sender (Optional[str]): Sender of event.
            hash (Optional[str]): Event hash.
            project_name (Optional[str]): Project name.
            username (Optional[str]): Username which triggered event.
            dependencies (Optional[list[str]]): List of event id dependencies.
            description (Optional[str]): Description of event.
            summary (Optional[dict[str, Any]]): Summary of event that can be used
                for simple filtering on listeners.
            payload (Optional[dict[str, Any]]): Full payload of event data with
                all details.
            finished (Optional[bool]): Mark event as finished on dispatch.
            store (Optional[bool]): Store event in event queue for possible
                future processing otherwise is event send only
                to active listeners.
        """

        if summary is None:
            summary = {}
        if payload is None:
            payload = {}
        event_data = {
            "topic": topic,
            "sender": sender,
            "hash": event_hash,
            "project": project_name,
            "user": username,
            "dependencies": dependencies,
            "description": description,
            "summary": summary,
            "payload": payload,
            "finished": finished,
            "store": store,
        }
        if self.post("events", **event_data):
            self.log.debug("Dispatched event {}".format(topic))
            return True
        self.log.error("Unable to dispatch event {}".format(topic))
        return False

    def enroll_event_job(
        self,
        source_topic,
        target_topic,
        sender,
        description=None,
        sequential=None,
        events_filter=None,
        max_retries=None,
    ):
        """Enroll job based on events.

        Enroll will find first unprocessed event with 'source_topic' and will
        create new event with 'target_topic' for it and return the new event
        data.

        Use 'sequential' to control that only single target event is created
        at same time. Creation of new target events is blocked while there is
        at least one unfinished event with target topic, when set to 'True'.
        This helps when order of events matter and more than one process using
        the same target is running at the same time.
        - Make sure the new event has updated status to '"finished"' status
            when you're done with logic

        Target topic should not clash with other processes/services.

        Created target event have 'dependsOn' key where is id of source topic.

        Use-case:
            - Service 1 is creating events with topic 'my.leech'
            - Service 2 process 'my.leech' and uses target topic 'my.process'
                - this service can run on 1-n machines
                - all events must be processed in a sequence by their creation
                    time and only one event can be processed at a time
                - in this case 'sequential' should be set to 'True' so only
                    one machine is actually processing events, but if one goes
                    down there are other that can take place
            - Service 3 process 'my.leech' and uses target topic 'my.discover'
                - this service can run on 1-n machines
                - order of events is not important
                - 'sequential' should be 'False'

        Args:
            source_topic (str): Source topic to enroll.
            target_topic (str): Topic of dependent event.
            sender (str): Identifier of sender (e.g. service name or username).
            description (Optional[str]): Human readable text shown
                in target event.
            sequential (Optional[bool]): The source topic must be processed
                in sequence.
            events_filter (Optional[dict[str, Any]]): Filtering conditions
                to filter the source event. For more technical specifications
                look to server backed 'ayon_server.sqlfilter.Filter'.
                TODO: Add example of filters.
            max_retries (Optional[int]): How many times can be event retried.
                Default value is based on server (3 at the time of this PR).

        Returns:
            Union[None, dict[str, Any]]: None if there is no event matching
                filters. Created event with 'target_topic'.
        """

        kwargs = {
            "sourceTopic": source_topic,
            "targetTopic": target_topic,
            "sender": sender,
        }
        if max_retries is not None:
            kwargs["maxRetries"] = max_retries
        if sequential is not None:
            kwargs["sequential"] = sequential
        if description is not None:
            kwargs["description"] = description
        if events_filter is not None:
            kwargs["filter"] = events_filter
        response = self.post("enroll", **kwargs)
        if response.status_code == 204:
            return None
        elif response.status_code >= 400:
            self.log.error(response.text)
            return None

        return response.data

    def _download_file(self, url, filepath, chunk_size, progress):
        dst_directory = os.path.dirname(filepath)
        if not os.path.exists(dst_directory):
            os.makedirs(dst_directory)

        kwargs = {"stream": True}
        if self._session is None:
            kwargs["headers"] = self.get_headers()
            get_func = self._base_functions_mapping[RequestTypes.get]
        else:
            get_func = self._session_functions_mapping[RequestTypes.get]

        with open(filepath, "wb") as f_stream:
            with get_func(url, **kwargs) as response:
                response.raise_for_status()
                progress.set_content_size(response.headers["Content-length"])
                for chunk in response.iter_content(chunk_size=chunk_size):
                    f_stream.write(chunk)
                    progress.add_transferred_chunk(len(chunk))

    def download_file(
        self, endpoint, filepath, chunk_size=None, progress=None
    ):
        """Download file from AYON server.

        Endpoint can be full url (must start with 'base_url' of api object).

        Progress object can be used to track download. Can be used when
        download happens in thread and other thread want to catch changes over
        time.

        Todos:
            Use retries and timeout.
            Return RestApiResponse.

        Args:
            endpoint (str): Endpoint or URL to file that should be downloaded.
            filepath (str): Path where file will be downloaded.
            chunk_size (Optional[int]): Size of chunks that are received
                in single loop.
            progress (Optional[TransferProgress]): Object that gives ability
                to track download progress.
        """

        if not chunk_size:
            chunk_size = self.default_download_chunk_size

        if endpoint.startswith(self._base_url):
            url = endpoint
        else:
            endpoint = endpoint.lstrip("/").rstrip("/")
            url = "{}/{}".format(self._rest_url, endpoint)

        # Create dummy object so the function does not have to check
        #   'progress' variable everywhere
        if progress is None:
            progress = TransferProgress()

        progress.set_source_url(url)
        progress.set_destination_url(filepath)
        progress.set_started()
        try:
            self._download_file(url, filepath, chunk_size, progress)

        except Exception as exc:
            progress.set_failed(str(exc))
            raise

        finally:
            progress.set_transfer_done()
        return progress

    @staticmethod
    def _upload_chunks_iter(file_stream, progress, chunk_size):
        """Generator that yields chunks of file.

        Args:
            file_stream (io.BinaryIO): Byte stream.
            progress (TransferProgress): Object to track upload progress.
            chunk_size (int): Size of chunks that are uploaded at once.

        Yields:
            bytes: Chunk of file.
        """

        # Get size of file
        file_stream.seek(0, io.SEEK_END)
        size = file_stream.tell()
        file_stream.seek(0)
        # Set content size to progress object
        progress.set_content_size(size)

        while True:
            chunk = file_stream.read(chunk_size)
            if not chunk:
                break
            progress.add_transferred_chunk(len(chunk))
            yield chunk

    def _upload_file(
        self,
        url,
        filepath,
        progress,
        request_type=None,
        chunk_size=None,
        **kwargs
    ):
        """

        Args:
            url (str): Url where file will be uploaded.
            filepath (str): Source filepath.
            progress (TransferProgress): Object that gives ability to track
                progress.
            request_type (Optional[RequestType]): Type of request that will
                be used. Default is PUT.
            chunk_size (Optional[int]): Size of chunks that are uploaded
                at once.
            **kwargs (Any): Additional arguments that will be passed
                to request function.

        Returns:
            RestApiResponse: Server response.
        """

        if request_type is None:
            request_type = RequestTypes.put

        if self._session is None:
            headers = kwargs.setdefault("headers", {})
            for key, value in self.get_headers().items():
                if key not in headers:
                    headers[key] = value
            post_func = self._base_functions_mapping[request_type]
        else:
            post_func = self._session_functions_mapping[request_type]

        if not chunk_size:
            chunk_size = self.default_upload_chunk_size

        with open(filepath, "rb") as stream:
            response = post_func(
                url,
                data=self._upload_chunks_iter(stream, progress, chunk_size),
                **kwargs
            )

        response.raise_for_status()
        return response

    def upload_file(
        self, endpoint, filepath, progress=None, request_type=None, **kwargs
    ):
        """Upload file to server.

        Todos:
            Use retries and timeout.
            Return RestApiResponse.

        Args:
            endpoint (str): Endpoint or url where file will be uploaded.
            filepath (str): Source filepath.
            progress (Optional[TransferProgress]): Object that gives ability
                to track upload progress.
            request_type (Optional[RequestType]): Type of request that will
                be used to upload file.
            **kwargs (Any): Additional arguments that will be passed
                to request function.

        Returns:
            requests.Response: Response object.
        """

        if endpoint.startswith(self._base_url):
            url = endpoint
        else:
            endpoint = endpoint.lstrip("/").rstrip("/")
            url = "{}/{}".format(self._rest_url, endpoint)

        # Create dummy object so the function does not have to check
        #   'progress' variable everywhere
        if progress is None:
            progress = TransferProgress()

        progress.set_source_url(filepath)
        progress.set_destination_url(url)
        progress.set_started()

        try:
            return self._upload_file(
                url, filepath, progress, request_type, **kwargs
            )

        except Exception as exc:
            progress.set_failed(str(exc))
            raise

        finally:
            progress.set_transfer_done()

    def trigger_server_restart(self):
        """Trigger server restart.

        Restart may be required when a change of specific value happened on
            server.
        """

        result = self.post("system/restart")
        if result.status_code != 204:
            # TODO add better exception
            raise ValueError("Failed to restart server")

    def query_graphql(self, query, variables=None):
        """Execute GraphQl query.

        Args:
            query (str): GraphQl query string.
            variables (Optional[dict[str, Any]): Variables that can be
                used in query.

        Returns:
            GraphQlResponse: Response from server.
        """

        data = {"query": query, "variables": variables or {}}
        response = self._do_rest_request(
            RequestTypes.post,
            self._graphql_url,
            json=data
        )
        response.raise_for_status()
        return GraphQlResponse(response)

    def get_graphql_schema(self):
        return self.query_graphql(INTROSPECTION_QUERY).data

    def get_server_schema(self):
        """Get server schema with info, url paths, components etc.

        Todos:
            Cache schema - How to find out it is outdated?

        Returns:
            dict[str, Any]: Full server schema.
        """

        url = "{}/openapi.json".format(self._base_url)
        response = self._do_rest_request(RequestTypes.get, url)
        if response:
            return response.data
        return None

    def get_schemas(self):
        """Get components schema.

        Name of components does not match entity type names e.g. 'project' is
        under 'ProjectModel'. We should find out some mapping. Also, there
        are properties which don't have information about reference to object
        e.g. 'config' has just object definition without reference schema.

        Returns:
            dict[str, Any]: Component schemas.
        """

        server_schema = self.get_server_schema()
        return server_schema["components"]["schemas"]

    def get_attributes_schema(self, use_cache=True):
        if not use_cache:
            self.reset_attributes_schema()

        if self._attributes_schema is None:
            result = self.get("attributes")
            if result.status_code != 200:
                raise UnauthorizedError(
                    "User must be authorized to receive attributes"
                )
            self._attributes_schema = result.data
        return copy.deepcopy(self._attributes_schema)

    def reset_attributes_schema(self):
        self._attributes_schema = None
        self._entity_type_attributes_cache = {}

    def set_attribute_config(
        self, attribute_name, data, scope, position=None, builtin=False
    ):
        if position is None:
            attributes = self.get("attributes").data["attributes"]
            origin_attr = next(
                (
                    attr for attr in attributes
                    if attr["name"] == attribute_name
                ),
                None
            )
            if origin_attr:
                position = origin_attr["position"]
            else:
                position = len(attributes)

        response = self.put(
            "attributes/{}".format(attribute_name),
            data=data,
            scope=scope,
            position=position,
            builtin=builtin
        )
        if response.status_code != 204:
            # TODO raise different exception
            raise ValueError(
                "Attribute \"{}\" was not created/updated. {}".format(
                    attribute_name, response.detail
                )
            )

        self.reset_attributes_schema()

    def remove_attribute_config(self, attribute_name):
        """Remove attribute from server.

        This can't be un-done, please use carefully.

        Args:
            attribute_name (str): Name of attribute to remove.
        """

        response = self.delete("attributes/{}".format(attribute_name))
        response.raise_for_status(
            "Attribute \"{}\" was not created/updated. {}".format(
                attribute_name, response.detail
            )
        )

        self.reset_attributes_schema()

    def get_attributes_for_type(self, entity_type):
        """Get attribute schemas available for an entity type.

        ```
        # Example attribute schema
        {
            # Common
            "type": "integer",
            "title": "Clip Out",
            "description": null,
            "example": 1,
            "default": 1,
            # These can be filled based on value of 'type'
            "gt": null,
            "ge": null,
            "lt": null,
            "le": null,
            "minLength": null,
            "maxLength": null,
            "minItems": null,
            "maxItems": null,
            "regex": null,
            "enum": null
        }
        ```

        Args:
            entity_type (str): Entity type for which should be attributes
                received.

        Returns:
            dict[str, dict[str, Any]]: Attribute schemas that are available
                for entered entity type.
        """
        attributes = self._entity_type_attributes_cache.get(entity_type)
        if attributes is None:
            attributes_schema = self.get_attributes_schema()
            attributes = {}
            for attr in attributes_schema["attributes"]:
                if entity_type not in attr["scope"]:
                    continue
                attr_name = attr["name"]
                attributes[attr_name] = attr["data"]

            self._entity_type_attributes_cache[entity_type] = attributes

        return copy.deepcopy(attributes)

    def get_attributes_fields_for_type(self, entity_type):
        """Prepare attribute fields for entity type.

        Returns:
            set[str]: Attributes fields for entity type.
        """

        attributes = self.get_attributes_for_type(entity_type)
        return {
            "attrib.{}".format(attr)
            for attr in attributes
        }

    def get_default_fields_for_type(self, entity_type):
        """Default fields for entity type.

        Returns most of commonly used fields from server.

        Args:
            entity_type (str): Name of entity type.

        Returns:
            set[str]: Fields that should be queried from server.
        """

        # Event does not have attributes
        if entity_type == "event":
            return set(DEFAULT_EVENT_FIELDS)

        if entity_type == "project":
            entity_type_defaults = set(DEFAULT_PROJECT_FIELDS)
            if not self.graphql_allows_data_in_query:
                entity_type_defaults.discard("data")

        elif entity_type == "folder":
            entity_type_defaults = set(DEFAULT_FOLDER_FIELDS)
            if not self.graphql_allows_data_in_query:
                entity_type_defaults.discard("data")

        elif entity_type == "task":
            entity_type_defaults = set(DEFAULT_TASK_FIELDS)
            if not self.graphql_allows_data_in_query:
                entity_type_defaults.discard("data")

        elif entity_type == "product":
            entity_type_defaults = set(DEFAULT_PRODUCT_FIELDS)
            if not self.graphql_allows_data_in_query:
                entity_type_defaults.discard("data")

        elif entity_type == "version":
            entity_type_defaults = set(DEFAULT_VERSION_FIELDS)
            if not self.graphql_allows_data_in_query:
                entity_type_defaults.discard("data")

        elif entity_type == "representation":
            entity_type_defaults = (
                DEFAULT_REPRESENTATION_FIELDS
                | REPRESENTATION_FILES_FIELDS
            )
            if not self.graphql_allows_data_in_query:
                entity_type_defaults.discard("data")

        elif entity_type == "productType":
            entity_type_defaults = set(DEFAULT_PRODUCT_TYPE_FIELDS)

        elif entity_type == "workfile":
            entity_type_defaults = set(DEFAULT_WORKFILE_INFO_FIELDS)
            if not self.graphql_allows_data_in_query:
                entity_type_defaults.discard("data")

        elif entity_type == "user":
            entity_type_defaults = set(DEFAULT_USER_FIELDS)

        else:
            raise ValueError("Unknown entity type \"{}\"".format(entity_type))
        return (
            entity_type_defaults
            | self.get_attributes_fields_for_type(entity_type)
        )

    def get_addons_info(self, details=True):
        """Get information about addons available on server.

        Args:
            details (Optional[bool]): Detailed data with information how
                to get client code.
        """

        endpoint = "addons"
        if details:
            endpoint += "?details=1"
        response = self.get(endpoint)
        response.raise_for_status()
        return response.data

    def get_addon_url(self, addon_name, addon_version, *subpaths):
        """Calculate url to addon route.

        Example:
            >>> api = ServerAPI("https://your.url.com")
            >>> api.get_addon_url(
            ...     "example", "1.0.0", "private", "my.zip")
            'https://your.url.com/addons/example/1.0.0/private/my.zip'

        Args:
            addon_name (str): Name of addon.
            addon_version (str): Version of addon.
            *subpaths (str): Any amount of subpaths that are added to
                addon url.

        Returns:
            str: Final url.
        """

        ending = ""
        if subpaths:
            ending = "/{}".format("/".join(subpaths))
        return "{}/addons/{}/{}{}".format(
            self._base_url,
            addon_name,
            addon_version,
            ending
        )

    def download_addon_private_file(
        self,
        addon_name,
        addon_version,
        filename,
        destination_dir,
        destination_filename=None,
        chunk_size=None,
        progress=None,
    ):
        """Download a file from addon private files.

        This method requires to have authorized token available. Private files
        are not under '/api' restpoint.

        Args:
            addon_name (str): Addon name.
            addon_version (str): Addon version.
            filename (str): Filename in private folder on server.
            destination_dir (str): Where the file should be downloaded.
            destination_filename (Optional[str]): Name of destination
                filename. Source filename is used if not passed.
            chunk_size (Optional[int]): Download chunk size.
            progress (Optional[TransferProgress]): Object that gives ability
                to track download progress.

        Returns:
            str: Filepath to downloaded file.
        """

        if not destination_filename:
            destination_filename = filename
        dst_filepath = os.path.join(destination_dir, destination_filename)
        # Filename can contain "subfolders"
        dst_dirpath = os.path.dirname(dst_filepath)
        if not os.path.exists(dst_dirpath):
            os.makedirs(dst_dirpath)

        url = self.get_addon_url(
            addon_name,
            addon_version,
            "private",
            filename
        )
        self.download_file(
            url, dst_filepath, chunk_size=chunk_size, progress=progress
        )
        return dst_filepath

    def get_installers(self, version=None, platform_name=None):
        """Information about desktop application installers on server.

        Desktop application installers are helpers to download/update AYON
        desktop application for artists.

        Args:
            version (Optional[str]): Filter installers by version.
            platform_name (Optional[str]): Filter installers by platform name.

        Returns:
            list[dict[str, Any]]:
        """

        query_fields = [
            "{}={}".format(key, value)
            for key, value in (
                ("version", version),
                ("platform", platform_name),
            )
            if value
        ]
        query = ""
        if query_fields:
            query = "?{}".format(",".join(query_fields))

        response = self.get("desktop/installers{}".format(query))
        response.raise_for_status()
        return response.data

    def create_installer(
        self,
        filename,
        version,
        python_version,
        platform_name,
        python_modules,
        runtime_python_modules,
        checksum,
        checksum_algorithm,
        file_size,
        sources=None,
    ):
        """Create new installer information on server.

        This step will create only metadata. Make sure to upload installer
            to the server using 'upload_installer' method.

        Runtime python modules are modules that are required to run AYON
            desktop application, but are not added to PYTHONPATH for any
            subprocess.

        Args:
            filename (str): Installer filename.
            version (str): Version of installer.
            python_version (str): Version of Python.
            platform_name (str): Name of platform.
            python_modules (dict[str, str]): Python modules that are available
                in installer.
            runtime_python_modules (dict[str, str]): Runtime python modules
                that are available in installer.
            checksum (str): Installer file checksum.
            checksum_algorithm (str): Type of checksum used to create checksum.
            file_size (int): File size.
            sources (Optional[list[dict[str, Any]]]): List of sources that
                can be used to download file.
        """

        body = {
            "filename": filename,
            "version": version,
            "pythonVersion": python_version,
            "platform": platform_name,
            "pythonModules": python_modules,
            "runtimePythonModules": runtime_python_modules,
            "checksum": checksum,
            "checksumAlgorithm": checksum_algorithm,
            "size": file_size,
        }
        if sources:
            body["sources"] = sources

        response = self.post("desktop/installers", **body)
        response.raise_for_status()

    def update_installer(self, filename, sources):
        """Update installer information on server.

        Args:
            filename (str): Installer filename.
            sources (list[dict[str, Any]]): List of sources that
                can be used to download file. Fully replaces existing sources.
        """

        response = self.patch(
            "desktop/installers/{}".format(filename),
            sources=sources
        )
        response.raise_for_status()

    def delete_installer(self, filename):
        """Delete installer from server.

        Args:
            filename (str): Installer filename.
        """

        response = self.delete("desktop/installers/{}".format(filename))
        response.raise_for_status()

    def download_installer(
        self,
        filename,
        dst_filepath,
        chunk_size=None,
        progress=None
    ):
        """Download installer file from server.

        Args:
            filename (str): Installer filename.
            dst_filepath (str): Destination filepath.
            chunk_size (Optional[int]): Download chunk size.
            progress (Optional[TransferProgress]): Object that gives ability
                to track download progress.
        """

        self.download_file(
            "desktop/installers/{}".format(filename),
            dst_filepath,
            chunk_size=chunk_size,
            progress=progress
        )

    def upload_installer(self, src_filepath, dst_filename, progress=None):
        """Upload installer file to server.

        Args:
            src_filepath (str): Source filepath.
            dst_filename (str): Destination filename.
            progress (Optional[TransferProgress]): Object that gives ability
                to track download progress.

        Returns:
            requests.Response: Response object.
        """

        return self.upload_file(
            "desktop/installers/{}".format(dst_filename),
            src_filepath,
            progress=progress
        )

    def _get_dependency_package_route(self, filename=None):
        endpoint = "desktop/dependencyPackages"
        if filename:
            return "{}/{}".format(endpoint, filename)
        return endpoint

    def get_dependency_packages(self):
        """Information about dependency packages on server.

        To download dependency package, use 'download_dependency_package'
        method and pass in 'filename'.

        Example data structure:
            {
                "packages": [
                    {
                        "filename": str,
                        "platform": str,
                        "checksum": str,
                        "checksumAlgorithm": str,
                        "size": int,
                        "sources": list[dict[str, Any]],
                        "supportedAddons": dict[str, str],
                        "pythonModules": dict[str, str]
                    }
                ]
            }

        Returns:
            dict[str, Any]: Information about dependency packages known for
                server.
        """

        endpoint = self._get_dependency_package_route()
        result = self.get(endpoint)
        result.raise_for_status()
        return result.data

    def create_dependency_package(
        self,
        filename,
        python_modules,
        source_addons,
        installer_version,
        checksum,
        checksum_algorithm,
        file_size,
        sources=None,
        platform_name=None,
    ):
        """Create dependency package on server.

        The package will be created on a server, it is also required to upload
        the package archive file (using 'upload_dependency_package').

        Args:
            filename (str): Filename of dependency package.
            python_modules (dict[str, str]): Python modules in dependency
                package.
                '{"<module name>": "<module version>", ...}'
            source_addons (dict[str, str]): Name of addons for which is
                dependency package created.
                '{"<addon name>": "<addon version>", ...}'
            installer_version (str): Version of installer for which was
                package created.
            checksum (str): Checksum of archive file where dependencies are.
            checksum_algorithm (str): Algorithm used to calculate checksum.
            file_size (Optional[int]): Size of file.
            sources (Optional[list[dict[str, Any]]]): Information about
                sources from where it is possible to get file.
            platform_name (Optional[str]): Name of platform for which is
                dependency package targeted. Default value is
                current platform.
        """

        post_body = {
            "filename": filename,
            "pythonModules": python_modules,
            "sourceAddons": source_addons,
            "installerVersion": installer_version,
            "checksum": checksum,
            "checksumAlgorithm": checksum_algorithm,
            "size": file_size,
            "platform": platform_name or platform.system().lower(),
        }
        if sources:
            post_body["sources"] = sources

        route = self._get_dependency_package_route()
        response = self.post(route, **post_body)
        response.raise_for_status()

    def update_dependency_package(self, filename, sources):
        """Update dependency package metadata on server.

        Args:
            filename (str): Filename of dependency package.
            sources (list[dict[str, Any]]): Information about
                sources from where it is possible to get file. Fully replaces
                existing sources.
        """

        response = self.patch(
            self._get_dependency_package_route(filename),
            sources=sources
        )
        response.raise_for_status()

    def delete_dependency_package(self, filename, platform_name=None):
        """Remove dependency package for specific platform.

        Args:
            filename (str): Filename of dependency package.
            platform_name (Optional[str]): Deprecated.
        """

        if platform_name is not None:
            warnings.warn(
                (
                    "Argument 'platform_name' is deprecated in"
                    " 'delete_dependency_package'. The argument will be"
                    " removed, please modify your code accordingly."
                ),
                DeprecationWarning
            )

        route = self._get_dependency_package_route(filename)
        response = self.delete(route)
        response.raise_for_status("Failed to delete dependency file")
        return response.data

    def download_dependency_package(
        self,
        src_filename,
        dst_directory,
        dst_filename,
        platform_name=None,
        chunk_size=None,
        progress=None,
    ):
        """Download dependency package from server.

        This method requires to have authorized token available. The package
        is only downloaded.

        Args:
            src_filename (str): Filename of dependency pacakge.
                For server version 0.2.0 and lower it is name of package
                to download.
            dst_directory (str): Where the file should be downloaded.
            dst_filename (str): Name of destination filename.
            platform_name (Optional[str]): Deprecated.
            chunk_size (Optional[int]): Download chunk size.
            progress (Optional[TransferProgress]): Object that gives ability
                to track download progress.

        Returns:
            str: Filepath to downloaded file.
        """

        if platform_name is not None:
            warnings.warn(
                (
                    "Argument 'platform_name' is deprecated in"
                    " 'download_dependency_package'. The argument will be"
                    " removed, please modify your code accordingly."
                ),
                DeprecationWarning
            )
        route = self._get_dependency_package_route(src_filename)
        package_filepath = os.path.join(dst_directory, dst_filename)
        self.download_file(
            route,
            package_filepath,
            chunk_size=chunk_size,
            progress=progress
        )
        return package_filepath

    def upload_dependency_package(
        self, src_filepath, dst_filename, platform_name=None, progress=None
    ):
        """Upload dependency package to server.

        Args:
            src_filepath (str): Path to a package file.
            dst_filename (str): Dependency package filename or name of package
                for server version 0.2.0 or lower. Must be unique.
            platform_name (Optional[str]): Deprecated.
            progress (Optional[TransferProgress]): Object to keep track about
                upload state.
        """

        if platform_name is not None:
            warnings.warn(
                (
                    "Argument 'platform_name' is deprecated in"
                    " 'upload_dependency_package'. The argument will be"
                    " removed, please modify your code accordingly."
                ),
                DeprecationWarning
            )

        route = self._get_dependency_package_route(dst_filename)
        self.upload_file(route, src_filepath, progress=progress)

    def upload_addon_zip(self, src_filepath, progress=None):
        """Upload addon zip file to server.

        File is validated on server. If it is valid, it is installed. It will
            create an event job which can be tracked (tracking part is not
            implemented yet).

        Example output:
            {'eventId': 'a1bfbdee27c611eea7580242ac120003'}

        Args:
            src_filepath (str): Path to a zip file.
            progress (Optional[TransferProgress]): Object to keep track about
                upload state.

        Returns:
            dict[str, Any]: Response data from server.
        """

        response = self.upload_file(
            "addons/install",
            src_filepath,
            progress=progress,
            request_type=RequestTypes.post,
        )
        return response.json()

    def get_bundles(self):
        """Server bundles with basic information.

        Example output:
            {
                "bundles": [
                    {
                        "name": "my_bundle",
                        "createdAt": "2023-06-12T15:37:02.420260",
                        "installerVersion": "1.0.0",
                        "addons": {
                            "core": "1.2.3"
                        },
                        "dependencyPackages": {
                            "windows": "a_windows_package123.zip",
                            "linux": "a_linux_package123.zip",
                            "darwin": "a_mac_package123.zip"
                        },
                        "isProduction": False,
                        "isStaging": False
                    }
                ],
                "productionBundle": "my_bundle",
                "stagingBundle": "test_bundle"
            }

        Returns:
            dict[str, Any]: Server bundles with basic information.
        """

        response = self.get("bundles")
        response.raise_for_status()
        return response.data

    def create_bundle(
        self,
        name,
        addon_versions,
        installer_version,
        dependency_packages=None,
        is_production=None,
        is_staging=None
    ):
        """Create bundle on server.

        Bundle cannot be changed once is created. Only isProduction, isStaging
        and dependency packages can change after creation.

        Args:
            name (str): Name of bundle.
            addon_versions (dict[str, str]): Addon versions.
            installer_version (Union[str, None]): Installer version.
            dependency_packages (Optional[dict[str, str]]): Dependency
                package names. Keys are platform names and values are name of
                packages.
            is_production (Optional[bool]): Bundle will be marked as
                production.
            is_staging (Optional[bool]): Bundle will be marked as staging.
        """

        body = {
            "name": name,
            "installerVersion": installer_version,
            "addons": addon_versions,
        }
        for key, value in (
            ("dependencyPackages", dependency_packages),
            ("isProduction", is_production),
            ("isStaging", is_staging),
        ):
            if value is not None:
                body[key] = value

        response = self.post("bundles", **body)
        response.raise_for_status()

    def update_bundle(
        self,
        bundle_name,
        dependency_packages=None,
        is_production=None,
        is_staging=None
    ):
        """Update bundle on server.

        Dependency packages can be update only for single platform. Others
        will be left untouched. Use 'None' value to unset dependency package
        from bundle.

        Args:
            bundle_name (str): Name of bundle.
            dependency_packages (Optional[dict[str, str]]): Dependency pacakge
                names that should be used with the bundle.
            is_production (Optional[bool]): Bundle will be marked as
                production.
            is_staging (Optional[bool]): Bundle will be marked as staging.
        """

        body = {
            key: value
            for key, value in (
                ("dependencyPackages", dependency_packages),
                ("isProduction", is_production),
                ("isStaging", is_staging),
            )
            if value is not None
        }
        response = self.patch(
            "{}/{}".format("bundles", bundle_name),
            **body
        )
        response.raise_for_status()

    def delete_bundle(self, bundle_name):
        """Delete bundle from server.

        Args:
            bundle_name (str): Name of bundle to delete.
        """

        response = self.delete(
            "{}/{}".format("bundles", bundle_name)
        )
        response.raise_for_status()

    # Anatomy presets
    def get_project_anatomy_presets(self):
        """Anatomy presets available on server.

        Content has basic information about presets. Example output:
            [
                {
                    "name": "netflix_VFX",
                    "primary": false,
                    "version": "1.0.0"
                },
                {
                    ...
                },
                ...
            ]

        Returns:
            list[dict[str, str]]: Anatomy presets available on server.
        """

        result = self.get("anatomy/presets")
        result.raise_for_status()
        return result.data.get("presets") or []

    def get_project_anatomy_preset(self, preset_name=None):
        """Anatomy preset values by name.

        Get anatomy preset values by preset name. Primary preset is returned
        if preset name is set to 'None'.

        Args:
            preset_name (Optional[str]): Preset name.

        Returns:
            dict[str, Any]: Anatomy preset values.
        """

        if preset_name is None:
            preset_name = "_"
        result = self.get("anatomy/presets/{}".format(preset_name))
        result.raise_for_status()
        return result.data

    def get_project_roots_by_site(self, project_name):
        """Root overrides per site name.

        Method is based on logged user and can't be received for any other
        user on server.

        Output will contain only roots per site id used by logged user.

        Args:
            project_name (str): Name of project.

        Returns:
             dict[str, dict[str, str]]: Root values by root name by site id.
        """

        result = self.get("projects/{}/roots".format(project_name))
        result.raise_for_status()
        return result.data

    def get_project_roots_for_site(self, project_name, site_id=None):
        """Root overrides for site.

        If site id is not passed a site set in current api object is used
        instead.

        Args:
            project_name (str): Name of project.
            site_id (Optional[str]): Id of site for which want to receive
                site overrides.

        Returns:
            dict[str, str]: Root values by root name or None if
                site does not have overrides.
        """

        if site_id is None:
            site_id = self.site_id

        if site_id is None:
            return {}
        roots = self.get_project_roots_by_site(project_name)
        return roots.get(site_id, {})

    def get_addon_settings_schema(
        self, addon_name, addon_version, project_name=None
    ):
        """Sudio/Project settings schema of an addon.

        Project schema may look differently as some enums are based on project
        values.

        Args:
            addon_name (str): Name of addon.
            addon_version (str): Version of addon.
            project_name (Optional[str]): Schema for specific project or
                default studio schemas.

        Returns:
            dict[str, Any]: Schema of studio/project settings.
        """

        args = tuple()
        if project_name:
            args = (project_name, )

        endpoint = self.get_addon_url(
            addon_name, addon_version, "schema", *args
        )
        result = self.get(endpoint)
        result.raise_for_status()
        return result.data

    def get_addon_site_settings_schema(self, addon_name, addon_version):
        """Site settings schema of an addon.

        Args:
            addon_name (str): Name of addon.
            addon_version (str): Version of addon.

        Returns:
            dict[str, Any]: Schema of site settings.
        """

        result = self.get("addons/{}/{}/siteSettings/schema".format(
            addon_name, addon_version
        ))
        result.raise_for_status()
        return result.data

    def get_addon_studio_settings(
        self,
        addon_name,
        addon_version,
        variant=None
    ):
        """Addon studio settings.

        Receive studio settings for specific version of an addon.

        Args:
            addon_name (str): Name of addon.
            addon_version (str): Version of addon.
            variant (Optional[Literal['production', 'staging']]): Name of
                settings variant. Used 'default_settings_variant' by default.

        Returns:
           dict[str, Any]: Addon settings.
        """

        if variant is None:
            variant = self.default_settings_variant

        query_items = {}
        if variant:
            query_items["variant"] = variant
        query = prepare_query_string(query_items)

        result = self.get(
            "addons/{}/{}/settings{}".format(addon_name, addon_version, query)
        )
        result.raise_for_status()
        return result.data

    def get_addon_project_settings(
        self,
        addon_name,
        addon_version,
        project_name,
        variant=None,
        site_id=None,
        use_site=True
    ):
        """Addon project settings.

        Receive project settings for specific version of an addon. The settings
        may be with site overrides when enabled.

        Site id is filled with current connection site id if not passed. To
        make sure any site id is used set 'use_site' to 'False'.

        Args:
            addon_name (str): Name of addon.
            addon_version (str): Version of addon.
            project_name (str): Name of project for which the settings are
                received.
            variant (Optional[Literal['production', 'staging']]): Name of
                settings variant. Used 'default_settings_variant' by default.
            site_id (Optional[str]): Name of site which is used for site
                overrides. Is filled with connection 'site_id' attribute
                if not passed.
            use_site (Optional[bool]): To force disable option of using site
                overrides set to 'False'. In that case won't be applied
                any site overrides.

        Returns:
            dict[str, Any]: Addon settings.
        """

        if not use_site:
            site_id = None
        elif not site_id:
            site_id = self.site_id

        query_items = {}
        if site_id:
            query_items["site"] = site_id

        if variant is None:
            variant = self.default_settings_variant

        if variant:
            query_items["variant"] = variant

        query = prepare_query_string(query_items)
        result = self.get(
            "addons/{}/{}/settings/{}{}".format(
                addon_name, addon_version, project_name, query
            )
        )
        result.raise_for_status()
        return result.data

    def get_addon_settings(
        self,
        addon_name,
        addon_version,
        project_name=None,
        variant=None,
        site_id=None,
        use_site=True
    ):
        """Receive addon settings.

        Receive addon settings based on project name value. Some arguments may
        be ignored if 'project_name' is set to 'None'.

        Args:
            addon_name (str): Name of addon.
            addon_version (str): Version of addon.
            project_name (Optional[str]): Name of project for which the
                settings are received. A studio settings values are received
                if is 'None'.
            variant (Optional[Literal['production', 'staging']]): Name of
                settings variant. Used 'default_settings_variant' by default.
            site_id (Optional[str]): Name of site which is used for site
                overrides. Is filled with connection 'site_id' attribute
                if not passed.
            use_site (Optional[bool]): To force disable option of using
                site overrides set to 'False'. In that case won't be applied
                any site overrides.

        Returns:
            dict[str, Any]: Addon settings.
        """

        if project_name is None:
            return self.get_addon_studio_settings(
                addon_name, addon_version, variant
            )
        return self.get_addon_project_settings(
            addon_name, addon_version, project_name, variant, site_id, use_site
        )

    def get_addon_site_settings(
        self, addon_name, addon_version, site_id=None
    ):
        """Site settings of an addon.

        If site id is not available an empty dictionary is returned.

        Args:
            addon_name (str): Name of addon.
            addon_version (str): Version of addon.
            site_id (Optional[str]): Name of site for which should be settings
                returned. using 'site_id' attribute if not passed.

        Returns:
            dict[str, Any]: Site settings.
        """

        if site_id is None:
            site_id = self.site_id

        if not site_id:
            return {}

        query = prepare_query_string({"site": site_id})
        result = self.get("addons/{}/{}/siteSettings{}".format(
            addon_name, addon_version, query
        ))
        result.raise_for_status()
        return result.data

    def get_bundle_settings(
        self,
        bundle_name=None,
        project_name=None,
        variant=None,
        site_id=None,
        use_site=True
    ):
        """Get complete set of settings for given data.

        If project is not passed then studio settings are returned. If variant
        is not passed 'default_settings_variant' is used. If bundle name is
        not passed then current production/staging bundle is used, based on
        variant value.

        Output contains addon settings and site settings in single dictionary.

        TODOs:
            - test how it behaves if there is not any bundle.
            - test how it behaves if there is not any production/staging
                bundle.

        Example output:
            {
                "addons": [
                    {
                        "name": "addon-name",
                        "version": "addon-version",
                        "settings": {...},
                        "siteSettings": {...}
                    }
                ]
            }

        Returns:
            dict[str, Any]: All settings for single bundle.
        """

        query_values = {
            key: value
            for key, value in (
                ("project_name", project_name),
                ("variant", variant or self.default_settings_variant),
                ("bundle_name", bundle_name),
            )
            if value
        }
        if use_site:
            if not site_id:
                site_id = self.site_id
            if site_id:
                query_values["site_id"] = site_id

        query = prepare_query_string(query_values)
        response = self.get("settings{}".format(query))
        response.raise_for_status()
        return response.data

    def get_addons_studio_settings(
        self,
        bundle_name=None,
        variant=None,
        site_id=None,
        use_site=True,
        only_values=True
    ):
        """All addons settings in one bulk.

        Warnings:
            Behavior of this function changed with AYON server version 0.3.0.
                Structure of output from server changed. If using
                'only_values=True' then output should be same as before.

        Args:
            bundle_name (Optional[str]): Name of bundle for which should be
                settings received.
            variant (Optional[Literal['production', 'staging']]): Name of
                settings variant. Used 'default_settings_variant' by default.
            site_id (Optional[str]): Id of site for which want to receive
                site overrides.
            use_site (bool): To force disable option of using site overrides
                set to 'False'. In that case won't be applied any site
                overrides.
            only_values (Optional[bool]): Output will contain only settings
                values without metadata about addons.

        Returns:
            dict[str, Any]: Settings of all addons on server.
        """

        output = self.get_bundle_settings(
            bundle_name=bundle_name,
            variant=variant,
            site_id=site_id,
            use_site=use_site
        )
        if only_values:
            output = {
                addon["name"]: addon["settings"]
                for addon in output["addons"]
            }
        return output

    def get_addons_project_settings(
        self,
        project_name,
        bundle_name=None,
        variant=None,
        site_id=None,
        use_site=True,
        only_values=True
    ):
        """Project settings of all addons.

        Server returns information about used addon versions, so full output
        looks like:
            {
                "settings": {...},
                "addons": {...}
            }

        The output can be limited to only values. To do so is 'only_values'
        argument which is by default set to 'True'. In that case output
        contains only value of 'settings' key.

        Warnings:
            Behavior of this function changed with AYON server version 0.3.0.
                Structure of output from server changed. If using
                'only_values=True' then output should be same as before.

        Args:
            project_name (str): Name of project for which are settings
                received.
            bundle_name (Optional[str]): Name of bundle for which should be
                settings received.
            variant (Optional[Literal['production', 'staging']]): Name of
                settings variant. Used 'default_settings_variant' by default.
            site_id (Optional[str]): Id of site for which want to receive
                site overrides.
            use_site (bool): To force disable option of using site overrides
                set to 'False'. In that case won't be applied any site
                overrides.
            only_values (Optional[bool]): Output will contain only settings
                values without metadata about addons.

        Returns:
            dict[str, Any]: Settings of all addons on server for passed
                project.
        """

        if not project_name:
            raise ValueError("Project name must be passed.")

        output = self.get_bundle_settings(
            project_name=project_name,
            bundle_name=bundle_name,
            variant=variant,
            site_id=site_id,
            use_site=use_site
        )
        if only_values:
            output = {
                addon["name"]: addon["settings"]
                for addon in output["addons"]
            }
        return output

    def get_addons_settings(
        self,
        bundle_name=None,
        project_name=None,
        variant=None,
        site_id=None,
        use_site=True,
        only_values=True
    ):
        """Universal function to receive all addon settings.

        Based on 'project_name' will receive studio settings or project
        settings. In case project is not passed is 'site_id' ignored.

        Warnings:
            Behavior of this function changed with AYON server version 0.3.0.
                Structure of output from server changed. If using
                'only_values=True' then output should be same as before.

        Args:
            bundle_name (Optional[str]): Name of bundle for which should be
                settings received.
            project_name (Optional[str]): Name of project for which should be
                settings received.
            variant (Optional[Literal['production', 'staging']]): Name of
                settings variant. Used 'default_settings_variant' by default.
            site_id (Optional[str]): Id of site for which want to receive
                site overrides.
            use_site (Optional[bool]): To force disable option of using site
                overrides set to 'False'. In that case won't be applied
                any site overrides.
            only_values (Optional[bool]): Only settings values will be
                returned. By default, is set to 'True'.
        """

        if project_name is None:
            return self.get_addons_studio_settings(
                bundle_name=bundle_name,
                variant=variant,
                site_id=site_id,
                use_site=use_site,
                only_values=only_values
            )

        return self.get_addons_project_settings(
            project_name=project_name,
            bundle_name=bundle_name,
            variant=variant,
            site_id=site_id,
            use_site=use_site,
            only_values=only_values
        )

    def get_secrets(self):
        """Get all secrets.

        Example output:
            [
                {
                    "name": "secret_1",
                    "value": "secret_value_1",
                },
                {
                    "name": "secret_2",
                    "value": "secret_value_2",
                }
            ]

        Returns:
            list[dict[str, str]]: List of secret entities.
        """

        response = self.get("secrets")
        response.raise_for_status()
        return response.data

    def get_secret(self, secret_name):
        """Get secret by name.

        Example output:
            {
                "name": "secret_name",
                "value": "secret_value",
            }

        Args:
            secret_name (str): Name of secret.

        Returns:
            dict[str, str]: Secret entity data.
        """

        response = self.get("secrets/{}".format(secret_name))
        response.raise_for_status()
        return response.data

    def save_secret(self, secret_name, secret_value):
        """Save secret.

        This endpoint can create and update secret.

        Args:
            secret_name (str): Name of secret.
            secret_value (str): Value of secret.
        """

        response = self.put(
            "secrets/{}".format(secret_name),
            name=secret_name,
            value=secret_value,
        )
        response.raise_for_status()
        return response.data


    def delete_secret(self, secret_name):
        """Delete secret by name.

        Args:
            secret_name (str): Name of secret to delete.
        """

        response = self.delete("secrets/{}".format(secret_name))
        response.raise_for_status()
        return response.data

    # Entity getters
    def get_rest_project(self, project_name):
        """Query project by name.

        This call returns project with anatomy data.

        Args:
            project_name (str): Name of project.

        Returns:
            Union[dict[str, Any], None]: Project entity data or 'None' if
                project was not found.
        """

        if not project_name:
            return None

        response = self.get("projects/{}".format(project_name))
        if response.status == 200:
            return response.data
        return None

    def get_rest_projects(self, active=True, library=None):
        """Query available project entities.

        User must be logged in.

        Args:
            active (Optional[bool]): Filter active/inactive projects. Both
                are returned if 'None' is passed.
            library (Optional[bool]): Filter standard/library projects. Both
                are returned if 'None' is passed.

        Returns:
            Generator[dict[str, Any]]: Available projects.
        """

        for project_name in self.get_project_names(active, library):
            project = self.get_rest_project(project_name)
            if project:
                yield project

    def get_rest_entity_by_id(self, project_name, entity_type, entity_id):
        """Get entity using REST on a project by its id.

        Args:
            project_name (str): Name of project where entity is.
            entity_type (Literal["folder", "task", "product", "version"]): The
                entity type which should be received.
            entity_id (str): Id of entity.

        Returns:
            dict[str, Any]: Received entity data.
        """

        if not all((project_name, entity_type, entity_id)):
            return None

        entity_endpoint = "{}s".format(entity_type)
        response = self.get("projects/{}/{}/{}".format(
            project_name, entity_endpoint, entity_id
        ))
        if response.status == 200:
            return response.data
        return None

    def get_rest_folder(self, project_name, folder_id):
        return self.get_rest_entity_by_id(project_name, "folder", folder_id)

    def get_rest_task(self, project_name, task_id):
        return self.get_rest_entity_by_id(project_name, "task", task_id)

    def get_rest_product(self, project_name, product_id):
        return self.get_rest_entity_by_id(project_name, "product", product_id)

    def get_rest_version(self, project_name, version_id):
        return self.get_rest_entity_by_id(project_name, "version", version_id)

    def get_rest_representation(self, project_name, representation_id):
        return self.get_rest_entity_by_id(
            project_name, "representation", representation_id
        )

    def get_project_names(self, active=True, library=None):
        """Receive available project names.

        User must be logged in.

        Args:
            active (Optional[bool]): Filter active/inactive projects. Both
                are returned if 'None' is passed.
            library (Optional[bool]): Filter standard/library projects. Both
                are returned if 'None' is passed.

        Returns:
            list[str]: List of available project names.
        """

        query_keys = {}
        if active is not None:
            query_keys["active"] = "true" if active else "false"

        if library is not None:
            query_keys["library"] = "true" if library else "false"
        query = ""
        if query_keys:
            query = "?{}".format(",".join([
                "{}={}".format(key, value)
                for key, value in query_keys.items()
            ]))

        response = self.get("projects{}".format(query), **query_keys)
        response.raise_for_status()
        data = response.data
        project_names = []
        if data:
            for project in data["projects"]:
                project_names.append(project["name"])
        return project_names

    def get_projects(
        self, active=True, library=None, fields=None, own_attributes=False
    ):
        """Get projects.

        Args:
            active (Optional[bool]): Filter active or inactive projects.
                Filter is disabled when 'None' is passed.
            library (Optional[bool]): Filter library projects. Filter is
                disabled when 'None' is passed.
            fields (Optional[Iterable[str]]): fields to be queried
                for project.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Generator[dict[str, Any]]: Queried projects.
        """

        if fields is None:
            use_rest = True
        else:
            use_rest = False
            fields = set(fields)
            for field in fields:
                if field.startswith("config"):
                    use_rest = True
                    break

        if use_rest:
            for project in self.get_rest_projects(active, library):
                if own_attributes:
                    fill_own_attribs(project)
                yield project

        else:
            if "attrib" in fields:
                fields.remove("attrib")
                fields |= self.get_attributes_fields_for_type("project")

            if own_attributes:
                fields.add("ownAttrib")

            query = projects_graphql_query(fields)
            for parsed_data in query.continuous_query(self):
                for project in parsed_data["projects"]:
                    if own_attributes:
                        fill_own_attribs(project)
                    yield project

    def get_project(self, project_name, fields=None, own_attributes=False):
        """Get project.

        Args:
            project_name (str): Name of project.
            fields (Optional[Iterable[str]]): fields to be queried
                for project.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict[str, Any], None]: Project entity data or None
                if project was not found.
        """

        use_rest = True
        if fields is not None:
            use_rest = False
            _fields = set()
            for field in fields:
                if field.startswith("config") or field == "data":
                    use_rest = True
                    break
                _fields.add(field)

            fields = _fields

        if use_rest:
            project = self.get_rest_project(project_name)
            if own_attributes:
                fill_own_attribs(project)
            return project

        if "attrib" in fields:
            fields.remove("attrib")
            fields |= self.get_attributes_fields_for_type("project")

        if own_attributes:
            fields.add("ownAttrib")
        query = project_graphql_query(fields)
        query.set_variable_value("projectName", project_name)

        parsed_data = query.query(self)

        project = parsed_data["project"]
        if project is not None:
            project["name"] = project_name
            if own_attributes:
                fill_own_attribs(project)
        return project

    def get_folders_hierarchy(
        self,
        project_name,
        search_string=None,
        folder_types=None
    ):
        """Get project hierarchy.

        All folders in project in hierarchy data structure.

        Example output:
            {
                "hierarchy": [
                    {
                        "id": "...",
                        "name": "...",
                        "label": "...",
                        "status": "...",
                        "folderType": "...",
                        "hasTasks": False,
                        "taskNames": [],
                        "parents": [],
                        "parentId": None,
                        "children": [...children folders...]
                    },
                    ...
                ]
            }

        Args:
            project_name (str): Project where to look for folders.
            search_string (Optional[str]): Search string to filter folders.
            folder_types (Optional[Iterable[str]]): Folder types to filter.

        Returns:
            dict[str, Any]: Response data from server.
        """

        if folder_types:
            folder_types = ",".join(folder_types)

        query_fields = [
            "{}={}".format(key, value)
            for key, value in (
                ("search", search_string),
                ("types", folder_types),
            )
            if value
        ]
        query = ""
        if query_fields:
            query = "?{}".format(",".join(query_fields))

        response = self.get(
            "projects/{}/hierarchy{}".format(project_name, query)
        )
        response.raise_for_status()
        return response.data

    def get_folders(
        self,
        project_name,
        folder_ids=None,
        folder_paths=None,
        folder_names=None,
        folder_types=None,
        parent_ids=None,
        folder_path_regex=None,
        has_products=None,
        has_tasks=None,
        has_children=None,
        statuses=None,
        tags=None,
        active=True,
        has_links=None,
        fields=None,
        own_attributes=False
    ):
        """Query folders from server.

        Todos:
            Folder name won't be unique identifier, so we should add folder path
                filtering.

        Notes:
            Filter 'active' don't have direct filter in GraphQl.

        Args:
            project_name (str): Name of project.
            folder_ids (Optional[Iterable[str]]): Folder ids to filter.
            folder_paths (Optional[Iterable[str]]): Folder paths used
                for filtering.
            folder_names (Optional[Iterable[str]]): Folder names used
                for filtering.
            folder_types (Optional[Iterable[str]]): Folder types used
                for filtering.
            parent_ids (Optional[Iterable[str]]): Ids of folder parents.
                Use 'None' if folder is direct child of project.
            folder_path_regex (Optional[str]): Folder path regex used
                for filtering.
            has_products (Optional[bool]): Filter folders with/without
                products. Ignored when None, default behavior.
            has_tasks (Optional[bool]): Filter folders with/without
                tasks. Ignored when None, default behavior.
            has_children (Optional[bool]): Filter folders with/without
                children. Ignored when None, default behavior.
            statuses (Optional[Iterable[str]]): Folder statuses used
                for filtering.
            tags (Optional[Iterable[str]]): Folder tags used
                for filtering.
            active (Optional[bool]): Filter active/inactive folders.
                Both are returned if is set to None.
            has_links (Optional[Literal[IN, OUT, ANY]]): Filter
                representations with IN/OUT/ANY links.
            fields (Optional[Iterable[str]]): Fields to be queried for
                folder. All possible folder fields are returned
                if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Generator[dict[str, Any]]: Queried folder entities.
        """

        if not project_name:
            return

        filters = {
            "projectName": project_name
        }
        if folder_ids is not None:
            folder_ids = set(folder_ids)
            if not folder_ids:
                return
            filters["folderIds"] = list(folder_ids)

        if folder_paths is not None:
            folder_paths = set(folder_paths)
            if not folder_paths:
                return
            filters["folderPaths"] = list(folder_paths)

        if folder_names is not None:
            folder_names = set(folder_names)
            if not folder_names:
                return
            filters["folderNames"] = list(folder_names)

        if folder_types is not None:
            folder_types = set(folder_types)
            if not folder_types:
                return
            filters["folderTypes"] = list(folder_types)

        if statuses is not None:
            statuses = set(statuses)
            if not statuses:
                return
            filters["folderStatuses"] = list(statuses)

        if tags is not None:
            tags = set(tags)
            if not tags:
                return
            filters["folderTags"] = list(tags)

        if parent_ids is not None:
            parent_ids = set(parent_ids)
            if not parent_ids:
                return
            if None in parent_ids:
                # Replace 'None' with '"root"' which is used during GraphQl
                #   query for parent ids filter for folders without folder
                #   parent
                parent_ids.remove(None)
                parent_ids.add("root")

            if project_name in parent_ids:
                # Replace project name with '"root"' which is used during
                #   GraphQl query for parent ids filter for folders without
                #   folder parent
                parent_ids.remove(project_name)
                parent_ids.add("root")

            filters["parentFolderIds"] = list(parent_ids)

        if folder_path_regex is not None:
            filters["folderPathRegex"] = folder_path_regex

        if has_products is not None:
            filters["folderHasProducts"] = has_products

        if has_tasks is not None:
            filters["folderHasTasks"] = has_tasks

        if has_links is not None:
            filters["folderHasLinks"] = has_links.upper()

        if has_children is not None:
            filters["folderHasChildren"] = has_children

        if not fields:
            fields = self.get_default_fields_for_type("folder")
        else:
            fields = set(fields)
            if "attrib" in fields:
                fields.remove("attrib")
                fields |= self.get_attributes_fields_for_type("folder")

        use_rest = False
        if "data" in fields and not self.graphql_allows_data_in_query:
            use_rest = True
            fields = {"id"}

        if active is not None:
            fields.add("active")

        if own_attributes and not use_rest:
            fields.add("ownAttrib")

        query = folders_graphql_query(fields)
        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        for parsed_data in query.continuous_query(self):
            for folder in parsed_data["project"]["folders"]:
                if active is not None and active is not folder["active"]:
                    continue

                if use_rest:
                    folder = self.get_rest_folder(project_name, folder["id"])
                else:
                    self._convert_entity_data(folder)

                if own_attributes:
                    fill_own_attribs(folder)
                yield folder

    def get_folder_by_id(
        self,
        project_name,
        folder_id,
        fields=None,
        own_attributes=False
    ):
        """Query folder entity by id.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            folder_id (str): Folder id.
            fields (Optional[Iterable[str]]): Fields that should be returned.
                All fields are returned if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict, None]: Folder entity data or None if was not found.
        """

        folders = self.get_folders(
            project_name,
            folder_ids=[folder_id],
            active=None,
            fields=fields,
            own_attributes=own_attributes
        )
        for folder in folders:
            return folder
        return None

    def get_folder_by_path(
        self,
        project_name,
        folder_path,
        fields=None,
        own_attributes=False
    ):
        """Query folder entity by path.

        Folder path is a path to folder with all parent names joined by slash.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            folder_path (str): Folder path.
            fields (Optional[Iterable[str]]): Fields that should be returned.
                All fields are returned if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict, None]: Folder entity data or None if was not found.
        """

        folders = self.get_folders(
            project_name,
            folder_paths=[folder_path],
            active=None,
            fields=fields,
            own_attributes=own_attributes
        )
        for folder in folders:
            return folder
        return None

    def get_folder_by_name(
        self,
        project_name,
        folder_name,
        fields=None,
        own_attributes=False
    ):
        """Query folder entity by path.

        Warnings:
            Folder name is not a unique identifier of a folder. Function is
                kept for OpenPype 3 compatibility.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            folder_name (str): Folder name.
            fields (Optional[Iterable[str]]): Fields that should be returned.
                All fields are returned if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict, None]: Folder entity data or None if was not found.
        """

        folders = self.get_folders(
            project_name,
            folder_names=[folder_name],
            active=None,
            fields=fields,
            own_attributes=own_attributes
        )
        for folder in folders:
            return folder
        return None

    def get_folder_ids_with_products(self, project_name, folder_ids=None):
        """Find folders which have at least one product.

        Folders that have at least one product should be immutable, so they
        should not change path -> change of name or name of any parent
        is not possible.

        Args:
            project_name (str): Name of project.
            folder_ids (Optional[Iterable[str]]): Limit folder ids filtering
                to a set of folders. If set to None all folders on project are
                checked.

        Returns:
            set[str]: Folder ids that have at least one product.
        """

        if folder_ids is not None:
            folder_ids = set(folder_ids)
            if not folder_ids:
                return set()

        query = folders_graphql_query({"id"})
        query.set_variable_value("projectName", project_name)
        query.set_variable_value("folderHasProducts", True)
        if folder_ids:
            query.set_variable_value("folderIds", list(folder_ids))

        parsed_data = query.query(self)
        folders = parsed_data["project"]["folders"]
        return {
            folder["id"]
            for folder in folders
        }

    def get_tasks(
        self,
        project_name,
        task_ids=None,
        task_names=None,
        task_types=None,
        folder_ids=None,
        assignees=None,
        assignees_all=None,
        statuses=None,
        tags=None,
        active=True,
        fields=None,
        own_attributes=False
    ):
        """Query task entities from server.

        Args:
            project_name (str): Name of project.
            task_ids (Iterable[str]): Task ids to filter.
            task_names (Iterable[str]): Task names used for filtering.
            task_types (Iterable[str]): Task types used for filtering.
            folder_ids (Iterable[str]): Ids of task parents. Use 'None'
                if folder is direct child of project.
            assignees (Optional[Iterable[str]]): Task assignees used for
                filtering. All tasks with any of passed assignees are
                returned.
            assignees_all (Optional[Iterable[str]]): Task assignees used
                for filtering. Task must have all of passed assignees to be
                returned.
            statuses (Optional[Iterable[str]]): Task statuses used for
                filtering.
            tags (Optional[Iterable[str]]): Task tags used for
                filtering.
            active (Optional[bool]): Filter active/inactive tasks.
                Both are returned if is set to None.
            fields (Optional[Iterable[str]]): Fields to be queried for
                folder. All possible folder fields are returned
                if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Generator[dict[str, Any]]: Queried task entities.
        """

        if not project_name:
            return

        filters = {
            "projectName": project_name
        }

        if task_ids is not None:
            task_ids = set(task_ids)
            if not task_ids:
                return
            filters["taskIds"] = list(task_ids)

        if task_names is not None:
            task_names = set(task_names)
            if not task_names:
                return
            filters["taskNames"] = list(task_names)

        if task_types is not None:
            task_types = set(task_types)
            if not task_types:
                return
            filters["taskTypes"] = list(task_types)

        if folder_ids is not None:
            folder_ids = set(folder_ids)
            if not folder_ids:
                return
            filters["folderIds"] = list(folder_ids)

        if assignees is not None:
            assignees = set(assignees)
            if not assignees:
                return
            filters["taskAssigneesAny"] = list(assignees)

        if assignees_all is not None:
            assignees_all = set(assignees_all)
            if not assignees_all:
                return
            filters["taskAssigneesAll"] = list(assignees_all)

        if statuses is not None:
            statuses = set(statuses)
            if not statuses:
                return
            filters["taskStatuses"] = list(statuses)

        if tags is not None:
            tags = set(tags)
            if not tags:
                return
            filters["taskTags"] = list(tags)

        if not fields:
            fields = self.get_default_fields_for_type("task")
        else:
            fields = set(fields)
            if "attrib" in fields:
                fields.remove("attrib")
                fields |= self.get_attributes_fields_for_type("task")

        use_rest = False
        if "data" in fields and not self.graphql_allows_data_in_query:
            use_rest = True
            fields = {"id"}

        if active is not None:
            fields.add("active")

        if own_attributes:
            fields.add("ownAttrib")

        query = tasks_graphql_query(fields)
        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        for parsed_data in query.continuous_query(self):
            for task in parsed_data["project"]["tasks"]:
                if active is not None and active is not task["active"]:
                    continue

                if use_rest:
                    task = self.get_rest_task(project_name, task["id"])
                else:
                    self._convert_entity_data(task)

                if own_attributes:
                    fill_own_attribs(task)
                yield task

    def get_task_by_name(
        self,
        project_name,
        folder_id,
        task_name,
        fields=None,
        own_attributes=False
    ):
        """Query task entity by name and folder id.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            folder_id (str): Folder id.
            task_name (str): Task name
            fields (Optional[Iterable[str]): Fields that should be returned.
                All fields are returned if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict, None]: Task entity data or None if was not found.
        """

        for task in self.get_tasks(
            project_name,
            folder_ids=[folder_id],
            task_names=[task_name],
            active=None,
            fields=fields,
            own_attributes=own_attributes
        ):
            return task
        return None

    def get_task_by_id(
        self,
        project_name,
        task_id,
        fields=None,
        own_attributes=False
    ):
        """Query task entity by id.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            task_id (str): Task id.
            fields (Optional[Iterable[str]): Fields that should be returned.
                All fields are returned if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict, None]: Task entity data or None if was not found.
        """

        for task in self.get_tasks(
            project_name,
            task_ids=[task_id],
            active=None,
            fields=fields,
            own_attributes=own_attributes
        ):
            return task
        return None

    def _filter_product(
        self, project_name, product, active, own_attributes, use_rest
    ):
        if active is not None and product["active"] is not active:
            return None

        if use_rest:
            product = self.get_rest_product(project_name, product["id"])
        else:
            self._convert_entity_data(product)

        if own_attributes:
            fill_own_attribs(product)

        return product

    def get_products(
        self,
        project_name,
        product_ids=None,
        product_names=None,
        folder_ids=None,
        product_types=None,
        product_name_regex=None,
        product_path_regex=None,
        names_by_folder_ids=None,
        statuses=None,
        tags=None,
        active=True,
        fields=None,
        own_attributes=False
    ):
        """Query products from server.

        Todos:
            Separate 'name_by_folder_ids' filtering to separated method. It
                cannot be combined with some other filters.

        Args:
            project_name (str): Name of project.
            product_ids (Optional[Iterable[str]]): Task ids to filter.
            product_names (Optional[Iterable[str]]): Task names used for
                filtering.
            folder_ids (Optional[Iterable[str]]): Ids of task parents.
                Use 'None' if folder is direct child of project.
            product_types (Optional[Iterable[str]]): Product types used for
                filtering.
            product_name_regex (Optional[str]): Filter products by name regex.
            product_path_regex (Optional[str]): Filter products by path regex.
                Path starts with folder path and ends with product name.
            names_by_folder_ids (Optional[dict[str, Iterable[str]]]): Product
                name filtering by folder id.
            statuses (Optional[Iterable[str]]): Product statuses used
                for filtering.
            tags (Optional[Iterable[str]]): Product tags used
                for filtering.
            active (Optional[bool]): Filter active/inactive products.
                Both are returned if is set to None.
            fields (Optional[Iterable[str]]): Fields to be queried for
                folder. All possible folder fields are returned
                if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Generator[dict[str, Any]]: Queried product entities.
        """

        if not project_name:
            return

        # Prepare these filters before 'name_by_filter_ids' filter
        filter_product_names = None
        if product_names is not None:
            filter_product_names = set(product_names)
            if not filter_product_names:
                return

        filter_folder_ids = None
        if folder_ids is not None:
            filter_folder_ids = set(folder_ids)
            if not filter_folder_ids:
                return

        # This will disable 'folder_ids' and 'product_names' filters
        #   - maybe could be enhanced in future?
        if names_by_folder_ids is not None:
            filter_product_names = set()
            filter_folder_ids = set()

            for folder_id, names in names_by_folder_ids.items():
                if folder_id and names:
                    filter_folder_ids.add(folder_id)
                    filter_product_names |= set(names)

            if not filter_product_names or not filter_folder_ids:
                return

        # Convert fields and add minimum required fields
        if fields:
            fields = set(fields) | {"id"}
            if "attrib" in fields:
                fields.remove("attrib")
                fields |= self.get_attributes_fields_for_type("product")
        else:
            fields = self.get_default_fields_for_type("product")

        use_rest = False
        if "data" in fields and not self.graphql_allows_data_in_query:
            use_rest = True
            fields = {"id"}

        if active is not None:
            fields.add("active")

        if own_attributes:
            fields.add("ownAttrib")

        # Add 'name' and 'folderId' if 'names_by_folder_ids' filter is entered
        if names_by_folder_ids:
            fields.add("name")
            fields.add("folderId")

        # Prepare filters for query
        filters = {
            "projectName": project_name
        }

        if filter_folder_ids:
            filters["folderIds"] = list(filter_folder_ids)

        if filter_product_names:
            filters["productNames"] = list(filter_product_names)

        if product_ids is not None:
            product_ids = set(product_ids)
            if not product_ids:
                return
            filters["productIds"] = list(product_ids)

        if product_types is not None:
            product_types = set(product_types)
            if not product_types:
                return
            filters["productTypes"] = list(product_types)

        if statuses is not None:
            statuses = set(statuses)
            if not statuses:
                return
            filters["productStatuses"] = list(statuses)

        if tags is not None:
            tags = set(tags)
            if not tags:
                return
            filters["productTags"] = list(tags)

        if product_name_regex:
            filters["productNameRegex"] = product_name_regex

        if product_path_regex:
            filters["productPathRegex"] = product_path_regex

        query = products_graphql_query(fields)
        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        parsed_data = query.query(self)

        products = parsed_data.get("project", {}).get("products", [])
        # Filter products by 'names_by_folder_ids'
        if names_by_folder_ids:
            products_by_folder_id = collections.defaultdict(list)
            for product in products:
                filtered_product = self._filter_product(
                    project_name, product, active, own_attributes, use_rest
                )
                if filtered_product is not None:
                    folder_id = filtered_product["folderId"]
                    products_by_folder_id[folder_id].append(filtered_product)

            for folder_id, names in names_by_folder_ids.items():
                for folder_product in products_by_folder_id[folder_id]:
                    if folder_product["name"] in names:
                        yield folder_product

        else:
            for product in products:
                filtered_product = self._filter_product(
                    project_name, product, active, own_attributes, use_rest
                )
                if filtered_product is not None:
                    yield filtered_product

    def get_product_by_id(
        self,
        project_name,
        product_id,
        fields=None,
        own_attributes=False
    ):
        """Query product entity by id.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            product_id (str): Product id.
            fields (Optional[Iterable[str]]): Fields that should be returned.
                All fields are returned if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict, None]: Product entity data or None if was not found.
        """

        products = self.get_products(
            project_name,
            product_ids=[product_id],
            active=None,
            fields=fields,
            own_attributes=own_attributes
        )
        for product in products:
            return product
        return None

    def get_product_by_name(
        self,
        project_name,
        product_name,
        folder_id,
        fields=None,
        own_attributes=False
    ):
        """Query product entity by name and folder id.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            product_name (str): Product name.
            folder_id (str): Folder id (Folder is a parent of products).
            fields (Optional[Iterable[str]]): Fields that should be returned.
                All fields are returned if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict, None]: Product entity data or None if was not found.
        """

        products = self.get_products(
            project_name,
            product_names=[product_name],
            folder_ids=[folder_id],
            active=None,
            fields=fields,
            own_attributes=own_attributes
        )
        for product in products:
            return product
        return None

    def get_product_types(self, fields=None):
        """Types of products.

        This is server wide information. Product types have 'name', 'icon' and
            'color'.

        Args:
            fields (Optional[Iterable[str]]): Product types fields to query.

        Returns:
            list[dict[str, Any]]: Product types information.
        """

        if not fields:
            fields = self.get_default_fields_for_type("productType")

        query = product_types_query(fields)

        parsed_data = query.query(self)

        return parsed_data.get("productTypes", [])

    def get_project_product_types(self, project_name, fields=None):
        """Types of products available on a project.

        Filter only product types available on project.

        Args:
            project_name (str): Name of project where to look for
                product types.
            fields (Optional[Iterable[str]]): Product types fields to query.

        Returns:
            list[dict[str, Any]]: Product types information.
        """

        if not fields:
            fields = self.get_default_fields_for_type("productType")

        query = project_product_types_query(fields)
        query.set_variable_value("projectName", project_name)

        parsed_data = query.query(self)

        return parsed_data.get("project", {}).get("productTypes", [])

    def get_product_type_names(self, project_name=None, product_ids=None):
        """Product type names.

        Warnings:
            This function will be probably removed. Matters if 'products_id'
                filter has real use-case.

        Args:
            project_name (Optional[str]): Name of project where to look for
                queried entities.
            product_ids (Optional[Iterable[str]]): Product ids filter. Can be
                used only with 'project_name'.

        Returns:
            set[str]: Product type names.
        """

        if project_name and product_ids:
            products = self.get_products(
                project_name,
                product_ids=product_ids,
                fields=["productType"],
                active=None,
            )
            return {
                product["productType"]
                for product in products
            }

        return {
            product_info["name"]
            for product_info in self.get_project_product_types(
                project_name, fields=["name"]
            )
        }

    def get_versions(
        self,
        project_name,
        version_ids=None,
        product_ids=None,
        versions=None,
        hero=True,
        standard=True,
        latest=None,
        statuses=None,
        tags=None,
        active=True,
        fields=None,
        own_attributes=False
    ):
        """Get version entities based on passed filters from server.

        Args:
            project_name (str): Name of project where to look for versions.
            version_ids (Optional[Iterable[str]]): Version ids used for
                version filtering.
            product_ids (Optional[Iterable[str]]): Product ids used for
                version filtering.
            versions (Optional[Iterable[int]]): Versions we're interested in.
            hero (Optional[bool]): Receive also hero versions when set to true.
            standard (Optional[bool]): Receive versions which are not hero when
                set to true.
            latest (Optional[bool]): Return only latest version of standard
                versions. This can be combined only with 'standard' attribute
                set to True.
            statuses (Optional[Iterable[str]]): Representation statuses used
                for filtering.
            tags (Optional[Iterable[str]]): Representation tags used
                for filtering.
            active (Optional[bool]): Receive active/inactive entities.
                Both are returned when 'None' is passed.
            fields (Optional[Iterable[str]]): Fields to be queried
                for version. All possible folder fields are returned
                if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Generator[dict[str, Any]]: Queried version entities.
        """

        if not fields:
            fields = self.get_default_fields_for_type("version")
        else:
            fields = set(fields)
            if "attrib" in fields:
                fields.remove("attrib")
                fields |= self.get_attributes_fields_for_type("version")

        # Make sure fields have minimum required fields
        fields |= {"id", "version"}

        use_rest = False
        if "data" in fields and not self.graphql_allows_data_in_query:
            use_rest = True
            fields = {"id"}

        if active is not None:
            fields.add("active")

        if own_attributes:
            fields.add("ownAttrib")

        filters = {
            "projectName": project_name
        }
        if version_ids is not None:
            version_ids = set(version_ids)
            if not version_ids:
                return
            filters["versionIds"] = list(version_ids)

        if product_ids is not None:
            product_ids = set(product_ids)
            if not product_ids:
                return
            filters["productIds"] = list(product_ids)

        # TODO versions can't be used as filter at this moment!
        if versions is not None:
            versions = set(versions)
            if not versions:
                return
            filters["versions"] = list(versions)

        if statuses is not None:
            statuses = set(statuses)
            if not statuses:
                return
            filters["versionStatuses"] = list(statuses)

        if tags is not None:
            tags = set(tags)
            if not tags:
                return
            filters["versionTags"] = list(tags)

        if not hero and not standard:
            return

        queries = []
        # Add filters based on 'hero' and 'standard'
        # NOTE: There is not a filter to "ignore" hero versions or to get
        #   latest and hero version
        # - if latest and hero versions should be returned it must be done in
        #       2 graphql queries
        if standard and not latest:
            # This query all versions standard + hero
            # - hero must be filtered out if is not enabled during loop
            query = versions_graphql_query(fields)
            for attr, filter_value in filters.items():
                query.set_variable_value(attr, filter_value)
            queries.append(query)
        else:
            if hero:
                # Add hero query if hero is enabled
                hero_query = versions_graphql_query(fields)
                for attr, filter_value in filters.items():
                    hero_query.set_variable_value(attr, filter_value)

                hero_query.set_variable_value("heroOnly", True)
                queries.append(hero_query)

            if standard:
                standard_query = versions_graphql_query(fields)
                for attr, filter_value in filters.items():
                    standard_query.set_variable_value(attr, filter_value)

                if latest:
                    standard_query.set_variable_value("latestOnly", True)
                queries.append(standard_query)

        for query in queries:
            for parsed_data in query.continuous_query(self):
                for version in parsed_data["project"]["versions"]:
                    if active is not None and version["active"] is not active:
                        continue

                    if not hero and version["version"] < 0:
                        continue

                    if use_rest:
                        version = self.get_rest_version(
                            project_name, version["id"]
                        )
                    else:
                        self._convert_entity_data(version)

                    if own_attributes:
                        fill_own_attribs(version)

                    yield version

    def get_version_by_id(
        self,
        project_name,
        version_id,
        fields=None,
        own_attributes=False
    ):
        """Query version entity by id.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            version_id (str): Version id.
            fields (Optional[Iterable[str]]): Fields that should be returned.
                All fields are returned if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict, None]: Version entity data or None if was not found.
       """

        versions = self.get_versions(
            project_name,
            version_ids=[version_id],
            active=None,
            hero=True,
            fields=fields,
            own_attributes=own_attributes
        )
        for version in versions:
            return version
        return None

    def get_version_by_name(
        self,
        project_name,
        version,
        product_id,
        fields=None,
        own_attributes=False
    ):
        """Query version entity by version and product id.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            version (int): Version of version entity.
            product_id (str): Product id. Product is a parent of version.
            fields (Optional[Iterable[str]]): Fields that should be returned.
                All fields are returned if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict, None]: Version entity data or None if was not found.
       """

        versions = self.get_versions(
            project_name,
            product_ids=[product_id],
            versions=[version],
            active=None,
            fields=fields,
            own_attributes=own_attributes
        )
        for version in versions:
            return version
        return None

    def get_hero_version_by_id(
        self,
        project_name,
        version_id,
        fields=None,
        own_attributes=False
    ):
        """Query hero version entity by id.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            version_id (int): Hero version id.
            fields (Optional[Iterable[str]]): Fields that should be returned.
                All fields are returned if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict, None]: Version entity data or None if was not found.
       """

        versions = self.get_hero_versions(
            project_name,
            version_ids=[version_id],
            fields=fields,
            own_attributes=own_attributes
        )
        for version in versions:
            return version
        return None

    def get_hero_version_by_product_id(
        self,
        project_name,
        product_id,
        fields=None,
        own_attributes=False
    ):
        """Query hero version entity by product id.

        Only one hero version is available on a product.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            product_id (int): Product id.
            fields (Optional[Iterable[str]]): Fields that should be returned.
                All fields are returned if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict, None]: Version entity data or None if was not found.
       """

        versions = self.get_hero_versions(
            project_name,
            product_ids=[product_id],
            fields=fields,
            own_attributes=own_attributes
        )
        for version in versions:
            return version
        return None

    def get_hero_versions(
        self,
        project_name,
        product_ids=None,
        version_ids=None,
        active=True,
        fields=None,
        own_attributes=False
    ):
        """Query hero versions by multiple filters.

        Only one hero version is available on a product.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            product_ids (Optional[Iterable[str]]): Product ids.
            version_ids (Optional[Iterable[str]]): Version ids.
            active (Optional[bool]): Receive active/inactive entities.
                Both are returned when 'None' is passed.
            fields (Optional[Iterable[str]]): Fields that should be returned.
                All fields are returned if 'None' is passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict, None]: Version entity data or None if was not found.
       """

        return self.get_versions(
            project_name,
            version_ids=version_ids,
            product_ids=product_ids,
            hero=True,
            standard=False,
            active=active,
            fields=fields,
            own_attributes=own_attributes
        )

    def get_last_versions(
        self,
        project_name,
        product_ids,
        active=True,
        fields=None,
        own_attributes=False
    ):
        """Query last version entities by product ids.

        Args:
            project_name (str): Project where to look for representation.
            product_ids (Iterable[str]): Product ids.
            active (Optional[bool]): Receive active/inactive entities.
                Both are returned when 'None' is passed.
            fields (Optional[Iterable[str]]): fields to be queried
                for representations.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            dict[str, dict[str, Any]]: Last versions by product id.
        """

        if fields:
            fields = set(fields)
            fields.add("productId")

        versions = self.get_versions(
            project_name,
            product_ids=product_ids,
            latest=True,
            active=active,
            fields=fields,
            own_attributes=own_attributes
        )
        return {
            version["productId"]: version
            for version in versions
        }

    def get_last_version_by_product_id(
        self,
        project_name,
        product_id,
        active=True,
        fields=None,
        own_attributes=False
    ):
        """Query last version entity by product id.

        Args:
            project_name (str): Project where to look for representation.
            product_id (str): Product id.
            active (Optional[bool]): Receive active/inactive entities.
                Both are returned when 'None' is passed.
            fields (Optional[Iterable[str]]): fields to be queried
                for representations.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict[str, Any], None]: Queried version entity or None.
        """

        versions = self.get_versions(
            project_name,
            product_ids=[product_id],
            latest=True,
            active=active,
            fields=fields,
            own_attributes=own_attributes
        )
        for version in versions:
            return version
        return None

    def get_last_version_by_product_name(
        self,
        project_name,
        product_name,
        folder_id,
        active=True,
        fields=None,
        own_attributes=False
    ):
        """Query last version entity by product name and folder id.

        Args:
            project_name (str): Project where to look for representation.
            product_name (str): Product name.
            folder_id (str): Folder id.
            active (Optional[bool]): Receive active/inactive entities.
                Both are returned when 'None' is passed.
            fields (Optional[Iterable[str]): fields to be queried
                for representations.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict[str, Any], None]: Queried version entity or None.
        """

        if not folder_id:
            return None

        product = self.get_product_by_name(
            project_name, product_name, folder_id, fields=["_id"]
        )
        if not product:
            return None
        return self.get_last_version_by_product_id(
            project_name,
            product["id"],
            active=active,
            fields=fields,
            own_attributes=own_attributes
        )

    def version_is_latest(self, project_name, version_id):
        """Is version latest from a product.

        Args:
            project_name (str): Project where to look for representation.
            version_id (str): Version id.

        Returns:
            bool: Version is latest or not.
        """

        query = GraphQlQuery("VersionIsLatest")
        project_name_var = query.add_variable(
            "projectName", "String!", project_name
        )
        version_id_var = query.add_variable(
            "versionId", "String!", version_id
        )
        project_query = query.add_field("project")
        project_query.set_filter("name", project_name_var)
        version_query = project_query.add_field("version")
        version_query.set_filter("id", version_id_var)
        product_query = version_query.add_field("product")
        latest_version_query = product_query.add_field("latestVersion")
        latest_version_query.add_field("id")

        parsed_data = query.query(self)
        latest_version = (
            parsed_data["project"]["version"]["product"]["latestVersion"]
        )
        return latest_version["id"] == version_id

    def _representation_conversion(self, representation):
        if "context" in representation:
            orig_context = representation["context"]
            context = {}
            if orig_context and orig_context != "null":
                context = json.loads(orig_context)
            representation["context"] = context

        repre_files = representation.get("files")
        if not repre_files:
            return

        for repre_file in repre_files:
            repre_file_size = repre_file.get("size")
            if repre_file_size is not None:
                repre_file["size"] = int(repre_file["size"])

    def get_representations(
        self,
        project_name,
        representation_ids=None,
        representation_names=None,
        version_ids=None,
        names_by_version_ids=None,
        statuses=None,
        tags=None,
        active=True,
        has_links=None,
        fields=None,
        own_attributes=False
    ):
        """Get representation entities based on passed filters from server.

        Todos:
            Add separated function for 'names_by_version_ids' filtering.
                Because can't be combined with others.

        Args:
            project_name (str): Name of project where to look for versions.
            representation_ids (Optional[Iterable[str]]): Representation ids
                used for representation filtering.
            representation_names (Optional[Iterable[str]]): Representation
                names used for representation filtering.
            version_ids (Optional[Iterable[str]]): Version ids used for
                representation filtering. Versions are parents of
                    representations.
            names_by_version_ids (Optional[bool]): Find representations
                by names and version ids. This filter discard all
                other filters.
            statuses (Optional[Iterable[str]]): Representation statuses used
                for filtering.
            tags (Optional[Iterable[str]]): Representation tags used
                for filtering.
            active (Optional[bool]): Receive active/inactive entities.
                Both are returned when 'None' is passed.
            has_links (Optional[Literal[IN, OUT, ANY]]): Filter
                representations with IN/OUT/ANY links.
            fields (Optional[Iterable[str]]): Fields to be queried for
                representation. All possible fields are returned if 'None' is
                passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Generator[dict[str, Any]]: Queried representation entities.
        """

        if not fields:
            fields = self.get_default_fields_for_type("representation")
        else:
            fields = set(fields)
            if "attrib" in fields:
                fields.remove("attrib")
                fields |= self.get_attributes_fields_for_type(
                    "representation"
                )

        use_rest = False
        if "data" in fields and not self.graphql_allows_data_in_query:
            use_rest = True
            fields = {"id"}

        if active is not None:
            fields.add("active")

        if own_attributes:
            fields.add("ownAttrib")

        filters = {
            "projectName": project_name
        }

        if representation_ids is not None:
            representation_ids = set(representation_ids)
            if not representation_ids:
                return
            filters["representationIds"] = list(representation_ids)

        version_ids_filter = None
        representaion_names_filter = None
        if names_by_version_ids is not None:
            version_ids_filter = set()
            representaion_names_filter = set()
            for version_id, names in names_by_version_ids.items():
                version_ids_filter.add(version_id)
                representaion_names_filter |= set(names)

            if not version_ids_filter or not representaion_names_filter:
                return

        else:
            if representation_names is not None:
                representaion_names_filter = set(representation_names)
                if not representaion_names_filter:
                    return

            if version_ids is not None:
                version_ids_filter = set(version_ids)
                if not version_ids_filter:
                    return

        if version_ids_filter:
            filters["versionIds"] = list(version_ids_filter)

        if representaion_names_filter:
            filters["representationNames"] = list(representaion_names_filter)

        if statuses is not None:
            statuses = set(statuses)
            if not statuses:
                return
            filters["representationStatuses"] = list(statuses)

        if tags is not None:
            tags = set(tags)
            if not tags:
                return
            filters["representationTags"] = list(tags)

        if has_links is not None:
            filters["representationHasLinks"] = has_links.upper()

        query = representations_graphql_query(fields)

        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        for parsed_data in query.continuous_query(self):
            for repre in parsed_data["project"]["representations"]:
                if active is not None and active is not repre["active"]:
                    continue

                if use_rest:
                    repre = self.get_rest_representation(
                        project_name, repre["id"]
                    )
                else:
                    self._convert_entity_data(repre)

                self._representation_conversion(repre)

                if own_attributes:
                    fill_own_attribs(repre)
                yield repre

    def get_representation_by_id(
        self,
        project_name,
        representation_id,
        fields=None,
        own_attributes=False
    ):
        """Query representation entity from server based on id filter.

        Args:
            project_name (str): Project where to look for representation.
            representation_id (str): Id of representation.
            fields (Optional[Iterable[str]]): fields to be queried
                for representations.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict[str, Any], None]: Queried representation entity or None.
        """

        representations = self.get_representations(
            project_name,
            representation_ids=[representation_id],
            active=None,
            fields=fields,
            own_attributes=own_attributes
        )
        for representation in representations:
            return representation
        return None

    def get_representation_by_name(
        self,
        project_name,
        representation_name,
        version_id,
        fields=None,
        own_attributes=False
    ):
        """Query representation entity by name and version id.

        Args:
            project_name (str): Project where to look for representation.
            representation_name (str): Representation name.
            version_id (str): Version id.
            fields (Optional[Iterable[str]]): fields to be queried
                for representations.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict[str, Any], None]: Queried representation entity or None.
        """

        representations = self.get_representations(
            project_name,
            representation_names=[representation_name],
            version_ids=[version_id],
            active=None,
            fields=fields,
            own_attributes=own_attributes
        )
        for representation in representations:
            return representation
        return None

    def get_representations_parents(self, project_name, representation_ids):
        """Find representations parents by representation id.

        Representation parent entities up to project.

        Args:
             project_name (str): Project where to look for entities.
             representation_ids (Iterable[str]): Representation ids.

        Returns:
            dict[str, RepresentationParents]: Parent entities by
                representation id.
        """

        if not representation_ids:
            return {}

        project = self.get_project(project_name)
        repre_ids = set(representation_ids)
        output = {
            repre_id: RepresentationParents(None, None, None, None)
            for repre_id in representation_ids
        }

        version_fields = self.get_default_fields_for_type("version")
        product_fields = self.get_default_fields_for_type("product")
        folder_fields = self.get_default_fields_for_type("folder")

        query = representations_parents_qraphql_query(
            version_fields, product_fields, folder_fields
        )
        query.set_variable_value("projectName", project_name)
        query.set_variable_value("representationIds", list(repre_ids))

        parsed_data = query.query(self)
        for repre in parsed_data["project"]["representations"]:
            repre_id = repre["id"]
            version = repre.pop("version")
            product = version.pop("product")
            folder = product.pop("folder")
            self._convert_entity_data(version)
            self._convert_entity_data(product)
            self._convert_entity_data(folder)
            output[repre_id] = RepresentationParents(
                version, product, folder, project
            )

        return output

    def get_representation_parents(self, project_name, representation_id):
        """Find representation parents by representation id.

        Representation parent entities up to project.

        Args:
             project_name (str): Project where to look for entities.
             representation_id (str): Representation id.

        Returns:
            RepresentationParents: Representation parent entities.
        """

        if not representation_id:
            return None

        parents_by_repre_id = self.get_representations_parents(
            project_name, [representation_id]
        )
        return parents_by_repre_id[representation_id]

    def get_repre_ids_by_context_filters(
        self,
        project_name,
        context_filters,
        representation_names=None,
        version_ids=None
    ):
        """Find representation ids which match passed context filters.

        Each representation has context integrated on representation entity in
        database. The context may contain project, folder, task name or
        product name, product type and many more. This implementation gives
        option to quickly filter representation based on representation data
        in database.

        Context filters have defined structure. To define filter of nested
            subfield use dot '.' as delimiter (For example 'task.name').
        Filter values can be regex filters. String or 're.Pattern' can be used.

        Args:
            project_name (str): Project where to look for representations.
            context_filters (dict[str, list[str]]): Filters of context fields.
            representation_names (Optional[Iterable[str]]): Representation
                names, can be used as additional filter for representations
                by their names.
            version_ids (Optional[Iterable[str]]): Version ids, can be used
                as additional filter for representations by their parent ids.

        Returns:
            list[str]: Representation ids that match passed filters.

        Example:
            The function returns just representation ids so if entities are
                required for funtionality they must be queried afterwards by
                their ids.
            >>> project_name = "testProject"
            >>> filters = {
            ...     "task.name": ["[aA]nimation"],
            ...     "product": [".*[Mm]ain"]
            ... }
            >>> repre_ids = get_repre_ids_by_context_filters(
            ...     project_name, filters)
            >>> repres = get_representations(project_name, repre_ids)
        """

        if not isinstance(context_filters, dict):
            raise TypeError(
                "Expected 'dict' got {}".format(str(type(context_filters)))
            )

        filter_body = {}
        if representation_names is not None:
            if not representation_names:
                return []
            filter_body["names"] = list(set(representation_names))

        if version_ids is not None:
            if not version_ids:
                return []
            filter_body["versionIds"] = list(set(version_ids))

        body_context_filters = []
        for key, filters in context_filters.items():
            if not isinstance(filters, (set, list, tuple)):
                raise TypeError(
                    "Expected 'set', 'list', 'tuple' got {}".format(
                        str(type(filters))))


            new_filters = set()
            for filter_value in filters:
                if isinstance(filter_value, PatternType):
                    filter_value = filter_value.pattern
                new_filters.add(filter_value)

            body_context_filters.append({
                "key": key,
                "values": list(new_filters)
            })

        response = self.post(
            "projects/{}/repreContextFilter".format(project_name),
            context=body_context_filters,
            **filter_body
        )
        response.raise_for_status()
        return response.data["ids"]

    def get_workfiles_info(
        self,
        project_name,
        workfile_ids=None,
        task_ids=None,
        paths=None,
        path_regex=None,
        statuses=None,
        tags=None,
        has_links=None,
        fields=None,
        own_attributes=False
    ):
        """Workfile info entities by passed filters.

        Args:
            project_name (str): Project under which the entity is located.
            workfile_ids (Optional[Iterable[str]]): Workfile ids.
            task_ids (Optional[Iterable[str]]): Task ids.
            paths (Optional[Iterable[str]]): Rootless workfiles paths.
            path_regex (Optional[str]): Regex filter for workfile path.
            statuses (Optional[Iterable[str]]): Workfile info statuses used
                for filtering.
            tags (Optional[Iterable[str]]): Workfile info tags used
                for filtering.
            has_links (Optional[Literal[IN, OUT, ANY]]): Filter
                representations with IN/OUT/ANY links.
            fields (Optional[Iterable[str]]): Fields to be queried for
                representation. All possible fields are returned if 'None' is
                passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Generator[dict[str, Any]]: Queried workfile info entites.
        """

        filters = {"projectName": project_name}
        if task_ids is not None:
            task_ids = set(task_ids)
            if not task_ids:
                return
            filters["taskIds"] = list(task_ids)

        if paths is not None:
            paths = set(paths)
            if not paths:
                return
            filters["paths"] = list(paths)

        if path_regex is not None:
            filters["workfilePathRegex"] = path_regex

        if workfile_ids is not None:
            workfile_ids = set(workfile_ids)
            if not workfile_ids:
                return
            filters["workfileIds"] = list(workfile_ids)

        if statuses is not None:
            statuses = set(statuses)
            if not statuses:
                return
            filters["workfileStatuses"] = list(statuses)

        if tags is not None:
            tags = set(tags)
            if not tags:
                return
            filters["workfileTags"] = list(tags)

        if has_links is not None:
            filters["workfilehasLinks"] = has_links.upper()

        if not fields:
            fields = self.get_default_fields_for_type("workfile")

        fields = set(fields)
        if "attrib" in fields:
            fields.remove("attrib")
            fields |= {
                "attrib.{}".format(attr)
                for attr in self.get_attributes_for_type("workfile")
            }
        if own_attributes:
            fields.add("ownAttrib")

        query = workfiles_info_graphql_query(fields)

        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        for parsed_data in query.continuous_query(self):
            for workfile_info in parsed_data["project"]["workfiles"]:
                if own_attributes:
                    fill_own_attribs(workfile_info)
                yield workfile_info

    def get_workfile_info(
        self, project_name, task_id, path, fields=None, own_attributes=False
    ):
        """Workfile info entity by task id and workfile path.

        Args:
            project_name (str): Project under which the entity is located.
            task_id (str): Task id.
            path (str): Rootless workfile path.
            fields (Optional[Iterable[str]]): Fields to be queried for
                representation. All possible fields are returned if 'None' is
                passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict[str, Any], None]: Workfile info entity or None.
        """

        if not task_id or not path:
            return None

        for workfile_info in self.get_workfiles_info(
            project_name,
            task_ids=[task_id],
            paths=[path],
            fields=fields,
            own_attributes=own_attributes
        ):
            return workfile_info
        return None

    def get_workfile_info_by_id(
        self, project_name, workfile_id, fields=None, own_attributes=False
    ):
        """Workfile info entity by id.

        Args:
            project_name (str): Project under which the entity is located.
            workfile_id (str): Workfile info id.
            fields (Optional[Iterable[str]]): Fields to be queried for
                representation. All possible fields are returned if 'None' is
                passed.
            own_attributes (Optional[bool]): Attribute values that are
                not explicitly set on entity will have 'None' value.

        Returns:
            Union[dict[str, Any], None]: Workfile info entity or None.
        """

        if not workfile_id:
            return None

        for workfile_info in self.get_workfiles_info(
            project_name,
            workfile_ids=[workfile_id],
            fields=fields,
            own_attributes=own_attributes
        ):
            return workfile_info
        return None

    def _prepare_thumbnail_content(self, project_name, response):
        content = None
        content_type = response.content_type

        # It is expected the response contains thumbnail id otherwise the
        #   content cannot be cached and filepath returned
        thumbnail_id = response.headers.get("X-Thumbnail-Id")
        if thumbnail_id is not None:
            content = response.content

        return ThumbnailContent(
            project_name, thumbnail_id, content, content_type
        )

    def get_thumbnail_by_id(self, project_name, thumbnail_id):
        """Get thumbnail from server by id.

        Permissions of thumbnails are related to entities so thumbnails must
        be queried per entity. So an entity type and entity type is required
        to be passed.

        Notes:
            It is recommended to use one of prepared entity type specific
                methods 'get_folder_thumbnail', 'get_version_thumbnail' or
                'get_workfile_thumbnail'.
            We do recommend pass thumbnail id if you have access to it. Each
                entity that allows thumbnails has 'thumbnailId' field, so it
                can be queried.

        Args:
            project_name (str): Project under which the entity is located.
            thumbnail_id (Optional[str]): DEPRECATED Use
                'get_thumbnail_by_id'.

        Returns:
            ThumbnailContent: Thumbnail content wrapper. Does not have to be
                valid.
        """

        response = self.raw_get(
            "projects/{}/thumbnails/{}".format(
                project_name,
                thumbnail_id
            )
        )
        return self._prepare_thumbnail_content(project_name, response)

    def get_thumbnail(
        self, project_name, entity_type, entity_id, thumbnail_id=None
    ):
        """Get thumbnail from server.

        Permissions of thumbnails are related to entities so thumbnails must
        be queried per entity. So an entity type and entity type is required
        to be passed.

        Notes:
            It is recommended to use one of prepared entity type specific
                methods 'get_folder_thumbnail', 'get_version_thumbnail' or
                'get_workfile_thumbnail'.
            We do recommend pass thumbnail id if you have access to it. Each
                entity that allows thumbnails has 'thumbnailId' field, so it
                can be queried.

        Args:
            project_name (str): Project under which the entity is located.
            entity_type (str): Entity type which passed entity id represents.
            entity_id (str): Entity id for which thumbnail should be returned.
            thumbnail_id (Optional[str]): DEPRECATED Use
                'get_thumbnail_by_id'.

        Returns:
            ThumbnailContent: Thumbnail content wrapper. Does not have to be
                valid.
        """

        if thumbnail_id:
            return self.get_thumbnail_by_id(project_name, thumbnail_id)

        if entity_type in (
            "folder",
            "version",
            "workfile",
        ):
            entity_type += "s"

        response = self.raw_get("projects/{}/{}/{}/thumbnail".format(
            project_name,
            entity_type,
            entity_id
        ))
        return self._prepare_thumbnail_content(project_name, response)

    def get_folder_thumbnail(
        self, project_name, folder_id, thumbnail_id=None
    ):
        """Prepared method to receive thumbnail for folder entity.

        Args:
            project_name (str): Project under which the entity is located.
            folder_id (str): Folder id for which thumbnail should be returned.
            thumbnail_id (Optional[str]): Prepared thumbnail id from entity.
                Used only to check if thumbnail was already cached.

        Returns:
            Union[str, None]: Path to downloaded thumbnail or none if entity
                does not have any (or if user does not have permissions).
        """

        return self.get_thumbnail(
            project_name, "folder", folder_id, thumbnail_id
        )

    def get_version_thumbnail(
        self, project_name, version_id, thumbnail_id=None
    ):
        """Prepared method to receive thumbnail for version entity.

        Args:
            project_name (str): Project under which the entity is located.
            version_id (str): Version id for which thumbnail should be
                returned.
            thumbnail_id (Optional[str]): Prepared thumbnail id from entity.
                Used only to check if thumbnail was already cached.

        Returns:
            Union[str, None]: Path to downloaded thumbnail or none if entity
                does not have any (or if user does not have permissions).
        """

        return self.get_thumbnail(
            project_name, "version", version_id, thumbnail_id
        )

    def get_workfile_thumbnail(
        self, project_name, workfile_id, thumbnail_id=None
    ):
        """Prepared method to receive thumbnail for workfile entity.

        Args:
            project_name (str): Project under which the entity is located.
            workfile_id (str): Worfile id for which thumbnail should be
                returned.
            thumbnail_id (Optional[str]): Prepared thumbnail id from entity.
                Used only to check if thumbnail was already cached.

        Returns:
            Union[str, None]: Path to downloaded thumbnail or none if entity
                does not have any (or if user does not have permissions).
        """

        return self.get_thumbnail(
            project_name, "workfile", workfile_id, thumbnail_id
        )

    def _get_thumbnail_mime_type(self, thumbnail_path):
        """Get thumbnail mime type on thumbnail creation based on source path.

        Args:
            thumbnail_path (str): Path to thumbnail source fie.

        Returns:
            str: Mime type used for thumbnail creation.

        Raises:
            ValueError: Mime type cannot be determined.
        """

        ext = os.path.splitext(thumbnail_path)[-1].lower()
        if ext == ".png":
            return "image/png"

        elif ext in (".jpeg", ".jpg"):
            return "image/jpeg"

        raise ValueError(
            "Thumbnail source file has unknown extensions {}".format(ext))

    def create_thumbnail(self, project_name, src_filepath, thumbnail_id=None):
        """Create new thumbnail on server from passed path.

        Args:
            project_name (str): Project where the thumbnail will be created
                and can be used.
            src_filepath (str): Filepath to thumbnail which should be uploaded.
            thumbnail_id (Optional[str]): Prepared if of thumbnail.

        Returns:
            str: Created thumbnail id.

        Raises:
            ValueError: When thumbnail source cannot be processed.
        """

        if not os.path.exists(src_filepath):
            raise ValueError("Entered filepath does not exist.")

        if thumbnail_id:
            self.update_thumbnail(
                project_name,
                thumbnail_id,
                src_filepath
            )
            return thumbnail_id

        mime_type = self._get_thumbnail_mime_type(src_filepath)
        response = self.upload_file(
            "projects/{}/thumbnails".format(project_name),
            src_filepath,
            request_type=RequestTypes.post,
            headers={"Content-Type": mime_type},
        )
        response.raise_for_status()
        return response.json()["id"]

    def update_thumbnail(self, project_name, thumbnail_id, src_filepath):
        """Change thumbnail content by id.

        Update can be also used to create new thumbnail.

        Args:
            project_name (str): Project where the thumbnail will be created
                and can be used.
            thumbnail_id (str): Thumbnail id to update.
            src_filepath (str): Filepath to thumbnail which should be uploaded.

        Raises:
            ValueError: When thumbnail source cannot be processed.
        """

        if not os.path.exists(src_filepath):
            raise ValueError("Entered filepath does not exist.")

        mime_type = self._get_thumbnail_mime_type(src_filepath)
        response = self.upload_file(
            "projects/{}/thumbnails/{}".format(project_name, thumbnail_id),
            src_filepath,
            request_type=RequestTypes.put,
            headers={"Content-Type": mime_type},
        )
        response.raise_for_status()

    def create_project(
        self,
        project_name,
        project_code,
        library_project=False,
        preset_name=None
    ):
        """Create project using Ayon settings.

        This project creation function is not validating project entity on
        creation. It is because project entity is created blindly with only
        minimum required information about project which is name and code.

        Entered project name must be unique and project must not exist yet.

        Note:
            This function is here to be OP v4 ready but in v3 has more logic
                to do. That's why inner imports are in the body.

        Args:
            project_name (str): New project name. Should be unique.
            project_code (str): Project's code should be unique too.
            library_project (Optional[bool]): Project is library project.
            preset_name (Optional[str]): Name of anatomy preset. Default is
                used if not passed.

        Raises:
            ValueError: When project name already exists.

        Returns:
            dict[str, Any]: Created project entity.
        """

        if self.get_project(project_name):
            raise ValueError("Project with name \"{}\" already exists".format(
                project_name
            ))

        if not PROJECT_NAME_REGEX.match(project_name):
            raise ValueError((
                "Project name \"{}\" contain invalid characters"
            ).format(project_name))

        preset = self.get_project_anatomy_preset(preset_name)

        result = self.post(
            "projects",
            name=project_name,
            code=project_code,
            anatomy=preset,
            library=library_project
        )

        if result.status != 201:
            details = "Unknown details ({})".format(result.status)
            if result.data:
                details = result.data.get("detail") or details
            raise ValueError("Failed to create project \"{}\": {}".format(
                project_name, details
            ))

        return self.get_project(project_name)

    def update_project(
        self,
        project_name,
        library=None,
        folder_types=None,
        task_types=None,
        link_types=None,
        statuses=None,
        tags=None,
        config=None,
        attrib=None,
        data=None,
        active=None,
        project_code=None,
        **changes
    ):
        """Update project entity on server.

        Args:
            project_name (str): Name of project.
            library (Optional[bool]): Change library state.
            folder_types (Optional[list[dict[str, Any]]]): Folder type
                definitions.
            task_types (Optional[list[dict[str, Any]]]): Task type
                definitions.
            link_types (Optional[list[dict[str, Any]]]): Link type
                definitions.
            statuses (Optional[list[dict[str, Any]]]): Status definitions.
            tags (Optional[list[dict[str, Any]]]): List of tags available to
                set on entities.
            config (Optional[dict[dict[str, Any]]]): Project anatomy config
                with templates and roots.
            attrib (Optional[dict[str, Any]]): Project attributes to change.
            data (Optional[dict[str, Any]]): Custom data of a project. This
                value will 100% override project data.
            active (Optional[bool]): Change active state of a project.
            project_code (Optional[str]): Change project code. Not recommended
                during production.
            **changes: Other changed keys based on Rest API documentation.
        """

        changes.update({
            key: value
            for key, value in (
                ("library", library),
                ("folderTypes", folder_types),
                ("taskTypes", task_types),
                ("linkTypes", link_types),
                ("statuses", statuses),
                ("tags", tags),
                ("config", config),
                ("attrib", attrib),
                ("data", data),
                ("active", active),
                ("code", project_code),
            )
            if value is not None
        })
        response = self.patch(
            "projects/{}".format(project_name),
            **changes
        )
        response.raise_for_status()

    def delete_project(self, project_name):
        """Delete project from server.

        This will completely remove project from server without any step back.

        Args:
            project_name (str): Project name that will be removed.
        """

        if not self.get_project(project_name):
            raise ValueError("Project with name \"{}\" was not found".format(
                project_name
            ))

        result = self.delete("projects/{}".format(project_name))
        if result.status_code != 204:
            raise ValueError(
                "Failed to delete project \"{}\". {}".format(
                    project_name, result.data["detail"]
                )
            )

    # --- Links ---
    def get_full_link_type_name(self, link_type_name, input_type, output_type):
        """Calculate full link type name used for query from server.

        Args:
            link_type_name (str): Type of link.
            input_type (str): Input entity type of link.
            output_type (str): Output entity type of link.

        Returns:
            str: Full name of link type used for query from server.
        """

        return "|".join([link_type_name, input_type, output_type])

    def get_link_types(self, project_name):
        """All link types available on a project.

        Example output:
            [
                {
                    "name": "reference|folder|folder",
                    "link_type": "reference",
                    "input_type": "folder",
                    "output_type": "folder",
                    "data": {}
                }
            ]

        Args:
            project_name (str): Name of project where to look for link types.

        Returns:
            list[dict[str, Any]]: Link types available on project.
        """

        response = self.get("projects/{}/links/types".format(project_name))
        response.raise_for_status()
        return response.data["types"]

    def get_link_type(
        self, project_name, link_type_name, input_type, output_type
    ):
        """Get link type data.

        There is not dedicated REST endpoint to get single link type,
        so method 'get_link_types' is used.

        Example output:
            {
                "name": "reference|folder|folder",
                "link_type": "reference",
                "input_type": "folder",
                "output_type": "folder",
                "data": {}
            }

        Args:
            project_name (str): Project where link type is available.
            link_type_name (str): Name of link type.
            input_type (str): Input entity type of link.
            output_type (str): Output entity type of link.

        Returns:
            Union[None, dict[str, Any]]: Link type information.
        """

        full_type_name = self.get_full_link_type_name(
            link_type_name, input_type, output_type
        )
        for link_type in self.get_link_types(project_name):
            if link_type["name"] == full_type_name:
                return link_type
        return None

    def create_link_type(
        self, project_name, link_type_name, input_type, output_type, data=None
    ):
        """Create or update link type on server.

        Warning:
            Because PUT is used for creation it is also used for update.

        Args:
            project_name (str): Project where link type is created.
            link_type_name (str): Name of link type.
            input_type (str): Input entity type of link.
            output_type (str): Output entity type of link.
            data (Optional[dict[str, Any]]): Additional data related to link.

        Raises:
            HTTPRequestError: Server error happened.
        """

        if data is None:
            data = {}
        full_type_name = self.get_full_link_type_name(
            link_type_name, input_type, output_type
        )
        response = self.put(
            "projects/{}/links/types/{}".format(project_name, full_type_name),
            **data
        )
        response.raise_for_status()

    def delete_link_type(
        self, project_name, link_type_name, input_type, output_type
    ):
        """Remove link type from project.

        Args:
            project_name (str): Project where link type is created.
            link_type_name (str): Name of link type.
            input_type (str): Input entity type of link.
            output_type (str): Output entity type of link.

        Raises:
            HTTPRequestError: Server error happened.
        """

        full_type_name = self.get_full_link_type_name(
            link_type_name, input_type, output_type
        )
        response = self.delete(
            "projects/{}/links/types/{}".format(project_name, full_type_name))
        response.raise_for_status()

    def make_sure_link_type_exists(
        self, project_name, link_type_name, input_type, output_type, data=None
    ):
        """Make sure link type exists on a project.

        Args:
            project_name (str): Name of project.
            link_type_name (str): Name of link type.
            input_type (str): Input entity type of link.
            output_type (str): Output entity type of link.
            data (Optional[dict[str, Any]]): Link type related data.
        """

        link_type = self.get_link_type(
            project_name, link_type_name, input_type, output_type)
        if (
            link_type
            and (data is None or data == link_type["data"])
        ):
            return
        self.create_link_type(
            project_name, link_type_name, input_type, output_type, data
        )

    def create_link(
        self,
        project_name,
        link_type_name,
        input_id,
        input_type,
        output_id,
        output_type
    ):
        """Create link between 2 entities.

        Link has a type which must already exists on a project.

        Example output:
            {
                "id": "59a212c0d2e211eda0e20242ac120002"
            }

        Args:
            project_name (str): Project where the link is created.
            link_type_name (str): Type of link.
            input_id (str): Id of input entity.
            input_type (str): Entity type of input entity.
            output_id (str): Id of output entity.
            output_type (str): Entity type of output entity.

        Returns:
            dict[str, str]: Information about link.

        Raises:
            HTTPRequestError: Server error happened.
        """

        full_link_type_name = self.get_full_link_type_name(
            link_type_name, input_type, output_type)
        response = self.post(
            "projects/{}/links".format(project_name),
            link=full_link_type_name,
            input=input_id,
            output=output_id
        )
        response.raise_for_status()
        return response.data

    def delete_link(self, project_name, link_id):
        """Remove link by id.

        Args:
            project_name (str): Project where link exists.
            link_id (str): Id of link.

        Raises:
            HTTPRequestError: Server error happened.
        """

        response = self.delete(
            "projects/{}/links/{}".format(project_name, link_id)
        )
        response.raise_for_status()

    def _prepare_link_filters(self, filters, link_types, link_direction):
        """Add links filters for GraphQl queries.

        Args:
            filters (dict[str, Any]): Object where filters will be added.
            link_types (Union[Iterable[str], None]): Link types filters.
            link_direction (Union[Literal["in", "out"], None]): Direction of
                link "in", "out" or 'None' for both.

        Returns:
            bool: Links are valid, and query from server can happen.
        """

        if link_types is not None:
            link_types = set(link_types)
            if not link_types:
                return False
            filters["linkTypes"] = list(link_types)

        if link_direction is not None:
            if link_direction not in ("in", "out"):
                return False
            filters["linkDirection"] = link_direction
        return True

    def get_entities_links(
        self,
        project_name,
        entity_type,
        entity_ids=None,
        link_types=None,
        link_direction=None
    ):
        """Helper method to get links from server for entity types.

        Example output:
            {
                "59a212c0d2e211eda0e20242ac120001": [
                    {
                        "id": "59a212c0d2e211eda0e20242ac120002",
                        "linkType": "reference",
                        "description": "reference link between folders",
                        "projectName": "my_project",
                        "author": "frantadmin",
                        "entityId": "b1df109676db11ed8e8c6c9466b19aa8",
                        "entityType": "folder",
                        "direction": "out"
                    },
                    ...
                ],
                ...
            }

        Args:
            project_name (str): Project where links are.
            entity_type (Literal["folder", "task", "product",
                "version", "representations"]): Entity type.
            entity_ids (Optional[Iterable[str]]): Ids of entities for which
                links should be received.
            link_types (Optional[Iterable[str]]): Link type filters.
            link_direction (Optional[Literal["in", "out"]]): Link direction
                filter.

        Returns:
            dict[str, list[dict[str, Any]]]: Link info by entity ids.
        """

        if entity_type == "folder":
            query_func = folders_graphql_query
            id_filter_key = "folderIds"
            project_sub_key = "folders"
        elif entity_type == "task":
            query_func = tasks_graphql_query
            id_filter_key = "taskIds"
            project_sub_key = "tasks"
        elif entity_type == "product":
            query_func = products_graphql_query
            id_filter_key = "productIds"
            project_sub_key = "products"
        elif entity_type == "version":
            query_func = versions_graphql_query
            id_filter_key = "versionIds"
            project_sub_key = "versions"
        elif entity_type == "representation":
            query_func = representations_graphql_query
            id_filter_key = "representationIds"
            project_sub_key = "representations"
        else:
            raise ValueError("Unknown type \"{}\". Expected {}".format(
                entity_type,
                ", ".join(
                    ("folder", "task", "product", "version", "representation")
                )
            ))

        output = collections.defaultdict(list)
        filters = {
            "projectName": project_name
        }
        if entity_ids is not None:
            entity_ids = set(entity_ids)
            if not entity_ids:
                return output
            filters[id_filter_key] = list(entity_ids)

        if not self._prepare_link_filters(filters, link_types, link_direction):
            return output

        query = query_func({"id", "links"})
        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        for parsed_data in query.continuous_query(self):
            for entity in parsed_data["project"][project_sub_key]:
                entity_id = entity["id"]
                output[entity_id].extend(entity["links"])
        return output

    def get_folders_links(
        self,
        project_name,
        folder_ids=None,
        link_types=None,
        link_direction=None
    ):
        """Query folders links from server.

        Args:
            project_name (str): Project where links are.
            folder_ids (Optional[Iterable[str]]): Ids of folders for which
                links should be received.
            link_types (Optional[Iterable[str]]): Link type filters.
            link_direction (Optional[Literal["in", "out"]]): Link direction
                filter.

        Returns:
            dict[str, list[dict[str, Any]]]: Link info by folder ids.
        """

        return self.get_entities_links(
            project_name, "folder", folder_ids, link_types, link_direction
        )

    def get_folder_links(
        self,
        project_name,
        folder_id,
        link_types=None,
        link_direction=None
    ):
        """Query folder links from server.

        Args:
            project_name (str): Project where links are.
            folder_id (str): Folder id for which links should be received.
            link_types (Optional[Iterable[str]]): Link type filters.
            link_direction (Optional[Literal["in", "out"]]): Link direction
                filter.

        Returns:
            list[dict[str, Any]]: Link info of folder.
        """

        return self.get_folders_links(
            project_name, [folder_id], link_types, link_direction
        )[folder_id]

    def get_tasks_links(
        self,
        project_name,
        task_ids=None,
        link_types=None,
        link_direction=None
    ):
        """Query tasks links from server.

        Args:
            project_name (str): Project where links are.
            task_ids (Optional[Iterable[str]]): Ids of tasks for which
                links should be received.
            link_types (Optional[Iterable[str]]): Link type filters.
            link_direction (Optional[Literal["in", "out"]]): Link direction
                filter.

        Returns:
            dict[str, list[dict[str, Any]]]: Link info by task ids.
        """

        return self.get_entities_links(
            project_name, "task", task_ids, link_types, link_direction
        )

    def get_task_links(
        self,
        project_name,
        task_id,
        link_types=None,
        link_direction=None
    ):
        """Query task links from server.

        Args:
            project_name (str): Project where links are.
            task_id (str): Task id for which links should be received.
            link_types (Optional[Iterable[str]]): Link type filters.
            link_direction (Optional[Literal["in", "out"]]): Link direction
                filter.

        Returns:
            list[dict[str, Any]]: Link info of task.
        """

        return self.get_tasks_links(
            project_name, [task_id], link_types, link_direction
        )[task_id]

    def get_products_links(
        self,
        project_name,
        product_ids=None,
        link_types=None,
        link_direction=None
    ):
        """Query products links from server.

        Args:
            project_name (str): Project where links are.
            product_ids (Optional[Iterable[str]]): Ids of products for which
                links should be received.
            link_types (Optional[Iterable[str]]): Link type filters.
            link_direction (Optional[Literal["in", "out"]]): Link direction
                filter.

        Returns:
            dict[str, list[dict[str, Any]]]: Link info by product ids.
        """

        return self.get_entities_links(
            project_name, "product", product_ids, link_types, link_direction
        )

    def get_product_links(
        self,
        project_name,
        product_id,
        link_types=None,
        link_direction=None
    ):
        """Query product links from server.

        Args:
            project_name (str): Project where links are.
            product_id (str): Product id for which links should be received.
            link_types (Optional[Iterable[str]]): Link type filters.
            link_direction (Optional[Literal["in", "out"]]): Link direction
                filter.

        Returns:
            list[dict[str, Any]]: Link info of product.
        """

        return self.get_products_links(
            project_name, [product_id], link_types, link_direction
        )[product_id]

    def get_versions_links(
        self,
        project_name,
        version_ids=None,
        link_types=None,
        link_direction=None
    ):
        """Query versions links from server.

        Args:
            project_name (str): Project where links are.
            version_ids (Optional[Iterable[str]]): Ids of versions for which
                links should be received.
            link_types (Optional[Iterable[str]]): Link type filters.
            link_direction (Optional[Literal["in", "out"]]): Link direction
                filter.

        Returns:
            dict[str, list[dict[str, Any]]]: Link info by version ids.
        """

        return self.get_entities_links(
            project_name, "version", version_ids, link_types, link_direction
        )

    def get_version_links(
        self,
        project_name,
        version_id,
        link_types=None,
        link_direction=None
    ):
        """Query version links from server.

        Args:
            project_name (str): Project where links are.
            version_id (str): Version id for which links should be received.
            link_types (Optional[Iterable[str]]): Link type filters.
            link_direction (Optional[Literal["in", "out"]]): Link direction
                filter.

        Returns:
            list[dict[str, Any]]: Link info of version.
        """

        return self.get_versions_links(
            project_name, [version_id], link_types, link_direction
        )[version_id]

    def get_representations_links(
        self,
        project_name,
        representation_ids=None,
        link_types=None,
        link_direction=None
    ):
        """Query representations links from server.

        Args:
            project_name (str): Project where links are.
            representation_ids (Optional[Iterable[str]]): Ids of
                representations for which links should be received.
            link_types (Optional[Iterable[str]]): Link type filters.
            link_direction (Optional[Literal["in", "out"]]): Link direction
                filter.

        Returns:
            dict[str, list[dict[str, Any]]]: Link info by representation ids.
        """

        return self.get_entities_links(
            project_name,
            "representation",
            representation_ids,
            link_types,
            link_direction
        )

    def get_representation_links(
        self,
        project_name,
        representation_id,
        link_types=None,
        link_direction=None
    ):
        """Query representation links from server.

        Args:
            project_name (str): Project where links are.
            representation_id (str): Representation id for which links
                should be received.
            link_types (Optional[Iterable[str]]): Link type filters.
            link_direction (Optional[Literal["in", "out"]]): Link direction
                filter.

        Returns:
            list[dict[str, Any]]: Link info of representation.
        """

        return self.get_representations_links(
            project_name, [representation_id], link_types, link_direction
        )[representation_id]

    # --- Batch operations processing ---
    def send_batch_operations(
        self,
        project_name,
        operations,
        can_fail=False,
        raise_on_fail=True
    ):
        """Post multiple CRUD operations to server.

        When multiple changes should be made on server side this is the best
        way to go. It is possible to pass multiple operations to process on a
        server side and do the changes in a transaction.

        Args:
            project_name (str): On which project should be operations
                processed.
            operations (list[dict[str, Any]]): Operations to be processed.
            can_fail (Optional[bool]): Server will try to process all
                operations even if one of them fails.
            raise_on_fail (Optional[bool]): Raise exception if an operation
                fails. You can handle failed operations on your own
                when set to 'False'.

        Raises:
            ValueError: Operations can't be converted to json string.
            FailedOperations: When output does not contain server operations
                or 'raise_on_fail' is enabled and any operation fails.

        Returns:
            list[dict[str, Any]]: Operations result with process details.
        """

        if not operations:
            return []

        body_by_id = {}
        operations_body = []
        for operation in operations:
            if not operation:
                continue

            op_id = operation.get("id")
            if not op_id:
                op_id = create_entity_id()
                operation["id"] = op_id

            try:
                body = json.loads(
                    json.dumps(operation, default=entity_data_json_default)
                )
            except:
                raise ValueError("Couldn't json parse body: {}".format(
                    json.dumps(
                        operation, indent=4, default=failed_json_default
                    )
                ))

            body_by_id[op_id] = body
            operations_body.append(body)

        if not operations_body:
            return []

        result = self.post(
            "projects/{}/operations".format(project_name),
            operations=operations_body,
            canFail=can_fail
        )

        op_results = result.get("operations")
        if op_results is None:
            raise FailedOperations(
                "Operation failed. Content: {}".format(str(result))
            )

        if result.get("success") or not raise_on_fail:
            return op_results

        for op_result in op_results:
            if not op_result["success"]:
                operation_id = op_result["id"]
                raise FailedOperations((
                    "Operation \"{}\" failed with data:\n{}\nDetail: {}."
                ).format(
                    operation_id,
                    json.dumps(body_by_id[operation_id], indent=4),
                    op_result["detail"],
                ))
        return op_results

    def _convert_entity_data(self, entity):
        if not entity:
            return
        entity_data = entity.get("data")
        if (
            entity_data is not None
            and isinstance(entity_data, six.string_types)
        ):
            entity["data"] = json.loads(entity_data)
