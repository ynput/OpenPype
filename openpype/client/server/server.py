import os
import json
import logging
import copy
from http import HTTPStatus

import requests

from .graphql import INTROSPECTION_QUERY

JSONDecodeError = getattr(json, "JSONDecodeError", ValueError)


class ServerError(Exception):
    pass


class UnauthorizedError(ServerError):
    pass


class AuthenticationError(ServerError):
    pass


class ServerNotReached(ServerError):
    pass


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


class MissingEntityError(Exception):
    pass


class ProjectNotFound(MissingEntityError):
    def __init__(self, project_name, message=None):
        if not message:
            message = "Project \"{}\" was not found".format(project_name)
        self.project_name = project_name
        super(ProjectNotFound, self).__init__(message)


class FolderNotFound(MissingEntityError):
    def __init__(self, project_name, folder_id, message=None):
        self.project_name = project_name
        self.folder_id = folder_id
        if not message:
            message = (
                "Folder with id \"{}\" was not found in project \"{}\""
            ).format(folder_id, project_name)
        super(FolderNotFound, self).__init__(message)


class RestApiResponse(object):
    """API Response."""

    def __init__(self, status_code, data=None):
        if data is None:
            data = {}
        self.status = status_code
        self.data = data

    @property
    def detail(self):
        return self.get("detail", HTTPStatus(self.status).description)

    @property
    def status_code(self):
        return self.status

    def __repr__(self):
        return "<{}: {} ({})>".format(
            self.__class__.__name__, self.status, self.detail
        )

    def __len__(self):
        return 200 <= self.status < 400

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)


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


class ServerAPIBase(object):
    """Base handler of connection to server.

    Requires url to server which is used as base for api and graphql calls.

    Login cause that a session is used

    Args:
        base_url(str): Example: http://localhost:5000
    """

    def __init__(self, base_url, token=None):
        if not base_url:
            raise ValueError("Invalid server URL {}".format(str(base_url)))

        base_url = base_url.rstrip("/")
        self._base_url = base_url
        self._rest_url = "{}/api".format(base_url)
        self._graphl_url = "{}/graphql".format(base_url)
        self._log = None
        self._access_token = token
        self._token_is_valid = None
        self._server_available = None

        self._session = None

        self._base_functions_mapping = {
            RequestTypes.get: requests.get,
            RequestTypes.post: requests.post,
            RequestTypes.put: requests.put,
            RequestTypes.patch: requests.patch,
            RequestTypes.delete: requests.delete
        }
        self._session_functions_mapping = {}
        # Variables related to attributes
        self._attributes_schema = None
        self._entity_type_attributes_cache = {}

    @property
    def access_token(self):
        return self._access_token

    @property
    def is_server_available(self):
        if self._server_available is None:
            response = requests.get(self._base_url)
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
            self.get_user_info()
            self._token_is_valid = True

        except UnauthorizedError:
            self._token_is_valid = False
        return self._token_is_valid

    def set_token(self, token):
        self.reset_token()
        self._access_token = token
        self.get_user_info()

    def reset_token(self):
        self._access_token = None
        self._token_validated = False
        self.close_session()

    def create_session(self):
        if self._session is not None:
            raise ValueError("Session is already created.")

        session = requests.Session()
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

        self._session.close()
        self._session = None
        self._session_functions_mapping = {}

    def get_user_info(self):
        response = self.get("users/me")
        if response.status != 200:
            raise UnauthorizedError("User is not authorized.")
        return response.data

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    def get_headers(self, content_type=None):
        if content_type is None:
            content_type = "application/json"
        headers = {"Content-Type": content_type}
        if self._access_token:
            headers["Authorization"] = "Bearer {}".format(self._access_token)
        return headers

    def login(self, username, password):
        if self.has_valid_token:
            try:
                user_info = self.get_user_info()
            except UnauthorizedError:
                user_info = {}

            current_username = user_info.get("name")
            if current_username == username:
                self.close_session()
                self.create_session()
                return

        self.reset_token()

        self.validate_server_availability()

        response = self.post(
            "auth/login",
            name=username,
            password=password
        )
        token = None
        if response:
            token = response["token"]
        self._access_token = token

        if not self.has_valid_token:
            raise AuthenticationError("Invalid credentials")
        self.create_session()

    def logout(self, soft=False):
        if self._access_token:
            if not soft:
                self._logout()
            self.reset_token()

    def _logout(self):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(self._access_token)
        }
        requests.post(
            self._base_url + "/api/auth/logout",
            headers=headers
        )

    def query_graphql(self, query, variables=None):
        data = {"query": query, "variables": variables or {}}
        response = self._do_rest_request(
            RequestTypes.post,
            self._graphl_url,
            json=data
        )
        return GraphQlResponse(response)

    def get_server_schema(self):
        """Get server schema with info, url paths, components etc.

        Todo:
            Cache schema - How to find out it is outdated?

        Returns:
            Dict[str, Any]: Full server schema.
        """

        url = "{}/openapi.json".format(self._base_url)
        response = self._do_rest_request(RequestTypes.get, url)
        if response:
            return response.data
        return None

    def get_schemas(self):
        """Get components schema.

        Name of components does not match entity type names e.g. 'project' is
        under 'ProjectModel'. We should find out some mapping. Also there
        are properties which don't have information about reference to object
        e.g. 'config' has just object definition without reference schema.

        Returns:
            Dict[str, Any]: Component schemas.
        """

        server_schema = self.get_server_schema()
        return server_schema["components"]["schemas"]

    def get_graphql_schema(self):
        return self.query_graphql(INTROSPECTION_QUERY).data

    def _do_rest_request(self, function, url, **kwargs):
        if self._session is None:
            if "headers" not in kwargs:
                kwargs["headers"] = self.get_headers()

            if isinstance(function, RequestType):
                function = self._base_functions_mapping[function]

        elif isinstance(function, RequestType):
            function = self._session_functions_mapping[function]

        try:
            response = function(url, **kwargs)
        except ConnectionRefusedError:
            response = RestApiResponse(
                500,
                {"detail": "Unable to connect the server. Connection refused"}
            )
        except requests.exceptions.ConnectionError:
            response = RestApiResponse(
                500,
                {"detail": "Unable to connect the server. Connection error"}
            )
        else:
            if response.text == "":
                response = RestApiResponse(response.status_code)
            else:
                try:
                    response = RestApiResponse(
                        response.status_code, response.json()
                    )
                except JSONDecodeError:
                    response = RestApiResponse(
                        500,
                        {
                            "detail": "The response is not a JSON: {}".format(
                                response.text)
                        }
                    )

        self.log.debug("Response {}".format(str(response)))
        return response

    def post(self, entrypoint, **kwargs):
        entrypoint = entrypoint.lstrip("/").rstrip("/")
        self.log.debug("Executing [POST] {}".format(entrypoint))
        url = "{}/{}".format(self._rest_url, entrypoint)
        return self._do_rest_request(
            RequestTypes.post,
            url,
            json=kwargs
        )

    def put(self, entrypoint, **kwargs):
        entrypoint = entrypoint.lstrip("/").rstrip("/")
        self.log.debug("Executing [PUT] {}".format(entrypoint))
        url = "{}/{}".format(self._rest_url, entrypoint)
        return self._do_rest_request(
            RequestTypes.put,
            url,
            json=kwargs
        )

    def patch(self, entrypoint, **kwargs):
        entrypoint = entrypoint.lstrip("/").rstrip("/")
        self.log.debug("Executing [PATCH] {}".format(entrypoint))
        url = "{}/{}".format(self._rest_url, entrypoint)
        return self._do_rest_request(
            RequestTypes.patch,
            url,
            json=kwargs
        )

    def get(self, entrypoint, **kwargs):
        entrypoint = entrypoint.lstrip("/").rstrip("/")
        self.log.debug("Executing [GET] {}".format(entrypoint))
        url = "{}/{}".format(self._rest_url, entrypoint)
        return self._do_rest_request(
            RequestTypes.get,
            url,
            params=kwargs
        )

    def delete(self, entrypoint, **kwargs):
        entrypoint = entrypoint.lstrip("/").rstrip("/")
        self.log.debug("Executing [DELETE] {}".format(entrypoint))
        url = "{}/{}".format(self._rest_url, entrypoint)
        return self._do_rest_request(
            RequestTypes.delete,
            url,
            params=kwargs
        )

    def get_rest_project(self, project_name):
        """Receive project by name.

        This call returns project with anatomy data.

        Args:
            project_name (str): Name of project.

        Returns:
            Union[Dict[str, Any], None]: Project entity data or 'None' if
                project was not found.
        """

        response = self.get("projects/{}".format(project_name))
        if response.status == 200:
            return response.data
        return None

    def get_rest_projects(self, active=None, library=None):
        """Receive available project entity data.

        User must be logged in.

        Args:
            active (bool): Filter active/inactive projects. Both are returned
                if 'None' is passed.
            library (bool): Filter standard/library projects. Both are
                returned if 'None' is passed.

        Returns:
            List[Dict[str, Any]]: List of available projects.
        """

        for project_name in self.get_project_names(active, library):
            project = self.get_rest_project(project_name)
            if project:
                yield project

    def get_project_names(self, active=None, library=None):
        """Receive available project names.

        User must be logged in.

        Args:
            active (bool): Filter active/inactive projects. Both are returned
                if 'None' is passed.
            library (bool): Filter standard/library projects. Both are
                returned if 'None' is passed.

        Returns:
            List[str]: List of available project names.
        """

        query_keys = {}
        if active is not None:
            query_keys["active"] = "true" if active else "false"

        if library is not None:
            query_keys["library"] = "true" if active else "false"
        query = ""
        if query_keys:
            query = "?{}".format(",".join([
                "{}={}".format(key, value)
                for key, value in query_keys.items()
            ]))

        response = self.get("projects{}".format(query), **query_keys)
        # TODO check status
        response.status
        data = response.data
        project_names = []
        if data:
            for project in data["projects"]:
                project_names.append(project["name"])
        return project_names

    def get_attributes_schema(self):
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

    def get_attributes_for_type(self, entity_type):
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


class ServerAPI(ServerAPIBase):
    """Extended server api which also handles storing tokens and url.

    Created object expect to have set environment variables
    'OPENPYPE_SERVER_URL'. Also is expecting filled 'OPENPYPE_TOKEN'
    but that can be filled afterwards with calling 'login' method.
    """

    def __init__(self):
        url = self.get_url()
        token = self.get_token()

        super(ServerAPI, self).__init__(url, token)

        self.validate_server_availability()
        self.create_session()

    def login(self, username, password):
        """Login to the server or change user.

        If user is the same as current user and token is available the
        login is skipped.
        """

        previous_token = self._access_token
        super(ServerAPI, self).login(username, password)
        if self.has_valid_token and previous_token != self._access_token:
            os.environ["OPENPYPE_TOKEN"] = self._access_token

    def logout(self):
        if not self._access_token:
            return

        try:
            from openpype_common.connection import logout

            logout(self._base_url, self._access_token)
            self.reset_token()

        except:
            self._logout()

    @staticmethod
    def get_url():
        return os.environ.get("OPENPYPE_SERVER_URL")

    @staticmethod
    def get_token():
        return os.environ.get("OPENPYPE_TOKEN")


class GlobalContext:
    """Singleton connection holder.

    Goal is to avoid create connection on import which can be dangerous in
    some cases.
    """

    _connection = None

    @classmethod
    def get_server_api_connection(cls):
        if cls._connection is None:
            cls._connection = ServerAPI()
        return cls._connection


def get_server_api_connection():
    """Access to global scope object of ServerAPI.

    This access expect to have set environment variables 'OPENPYPE_SERVER_URL'
    and 'OPENPYPE_TOKEN'.

    Returns:
        ServerAPI: Object of connection to server.
    """

    return GlobalContext.get_server_api_connection()


def get(*args, **kwargs):
    con = get_server_api_connection()
    return con.get(*args, **kwargs)


def post(*args, **kwargs):
    con = get_server_api_connection()
    return con.post(*args, **kwargs)


def put(*args, **kwargs):
    con = get_server_api_connection()
    return con.put(*args, **kwargs)


def patch(*args, **kwargs):
    con = get_server_api_connection()
    return con.patch(*args, **kwargs)


def delete(*args, **kwargs):
    con = get_server_api_connection()
    return con.delete(*args, **kwargs)
