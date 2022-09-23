import os
import json
import logging
import collections
from http import HTTPStatus
import requests
import six

JSONDecodeError = getattr(json, "JSONDecodeError", ValueError)


class ServerError(Exception):
    pass


class UnauthorizedError(ServerError):
    pass


class AuthenticationError(ServerError):
    pass


class ServerNotReached(ServerError):
    pass


def store_token(token):
    filepath = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "token"
    )
    with open(filepath, "w") as stream:
        stream.write(token)


def load_token():
    filepath = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "token"
    )
    if os.path.exists(filepath):
        with open(filepath, "r") as stream:
            token = stream.read()
        return str(token)
    return ""


class RequestType:
    def __init__(self, name):
        self.name = name


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

    def __init__(self, status_code=200, **data):
        self.status = status_code
        self.data = data

    @property
    def detail(self):
        return self.get("detail", HTTPStatus(self.status).description)

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
    """
    Args:
        base_url(str): Example: http://localhost:5000
    """

    def __init__(self, base_url, token=None):
        base_url = base_url.rstrip("/")
        self._base_url = base_url
        self._rest_url = "{}/api".format(base_url)
        self._graphl_url = "{}/graphql".format(base_url)
        self._log = None
        self._access_token = token
        self._token_is_valid = None
        self._server_available = None

        self._base_functions_mapping = {
            RequestTypes.get: requests.get,
            RequestTypes.post: requests.post,
            RequestTypes.put: requests.put,
            RequestTypes.patch: requests.patch,
            RequestTypes.delete: requests.delete
        }

    @property
    def access_token(self):
        return self._access_token

    @property
    def is_server_available(self):
        if self._server_available is None:
            response = self.get(self._base_url)
            self._server_available = response.status == 200
        return self._server_available

    @property
    def has_valid_token(self):
        if self._access_token is None:
            return False

        if self._token_is_valid is None:
            self.validate_token()
        return self._token_is_valid

    def validate_token(self):
        try:
            self.get_user_info()
            self._token_is_valid = True

        except UnauthorizedError:
            self._token_is_valid = False
        return self._token_is_valid

    def invalidate_token(self):
        self._access_token = None
        self._token_validated = False

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

    def login(self, name, password):
        token = load_token()
        if token:
            self._access_token = token
            response = self.get("users/me")
            if response.status == 200 and response.data["name"] == name:
                return
            self._access_token = None
            store_token("")

        response = self._do_rest_request(
            RequestTypes.get,
            self._rest_url
        )
        response = self.post(
            "auth/login",
            name=name,
            password=password
        )
        if response:
            self._access_token = response["token"]
            store_token(self._access_token)

    def logout(self):
        if self._access_token:
            return self.post("auth/logout")

    def query(self, query, variables=None):
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

    def _do_rest_request(self, function, url, **kwargs):
        if "headers" not in kwargs:
            kwargs["headers"] = self.get_headers()

        if isinstance(function, RequestType):
            function = self._base_functions_mapping[function]

        try:
            response = function(url, **kwargs)
        except ConnectionRefusedError:
            response = RestApiResponse(
                500,
                detail="Unable to connect the server. Connection refused"
            )
        except requests.exceptions.ConnectionError:
            response = RestApiResponse(
                500,
                detail="Unable to connect the server. Connection error"
            )
        else:
            if response.text == "":
                data = None
                response = RestApiResponse(response.status_code)
            else:
                try:
                    data = response.json()
                except JSONDecodeError:
                    response = RestApiResponse(
                        500,
                        detail="The response is not a JSON: {}".format(
                            response.text
                        )
                    )
                else:
                    response = RestApiResponse(response.status_code, **data)
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


class ServerAPI(ServerAPIBase):
    def get_rest_project(self, project_name):
        response = self.get("projects/{}".format(project_name))
        return response.data

    def get_rest_projects(self, active=None, library=None):
        for project_name in self.get_project_names(active, library):
            project = self.get_rest_project(project_name)
            if project:
                yield project

    def get_project_names(self, active=None, library=None):
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

    def get_project(self, project_name):
        output = self.get("projects/{}".format(project_name)).data
        if output.get("code") == 404:
            return None
        return output


class GlobalContext:
    _connection = None

    @classmethod
    def get_server_api_connection(cls):
        if cls._connection is None:
            # Fill to start work
            # NOTE: This is not how it should be in production !!!
            url = os.environ.get("OPENPYPE_SERVER_URL")
            username = os.environ.get("OPENPYPE_SERVER_USER")
            password = os.environ.get("OPENPYPE_SERVER_PASS")
            con = ServerAPI(url)
            con.login(username, password)
            cls._connection = con
        return cls._connection


def get_server_api_connection():
    return GlobalContext.get_server_api_connection()
