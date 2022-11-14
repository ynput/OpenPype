import json
import logging
import collections
import copy
from http import HTTPStatus

import requests

from .constants import (
    DEFAULT_PROJECT_FIELDS,
    DEFAULT_FOLDER_FIELDS,
    DEFAULT_TASK_FIELDS,
    DEFAULT_SUBSET_FIELDS,
    DEFAULT_VERSION_FIELDS,
    DEFAULT_REPRESENTATION_FIELDS,
    REPRESENTATION_FILES_FIELDS,
    DEFAULT_WORKFILE_INFO_FIELDS,
)
from .graphql import GraphQlQuery, INTROSPECTION_QUERY
from .graphql_queries import (
    project_graphql_query,
    projects_graphql_query,
    folders_graphql_query,
    folders_tasks_graphql_query,
    tasks_graphql_query,
    subsets_graphql_query,
    versions_graphql_query,
    representations_graphql_query,
    representations_parents_qraphql_query,
    workfiles_info_graphql_query,
)

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

    def __init__(self, status_code, data=None, content=None, headers=None):
        if data is None:
            data = {}
        self.status = status_code
        self.data = data
        self.content = content
        self.headers = headers or {}

    def __getattr__(self, attr):
        return getattr(self._response, attr)

    @property
    def content_type(self):
        return self.headers.get("Content-Type")

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

        # Attributes cache
        self._attributes_schema = None
        self._entity_type_attributes_cache = {}

        self._thumbnail_cache = ThumbnailCache(True)

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
        self._token_is_valid = None
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
        if response.status_code != 200:
            _detail = response.data.get("detail")
            details = ""
            if _detail:
                details = " {}".format(_detail)

            raise AuthenticationError("Login failed {}".format(details))

        self._access_token = response["token"]

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
            new_response = RestApiResponse(
                500,
                {"detail": "Unable to connect the server. Connection refused"}
            )
        except requests.exceptions.ConnectionError:
            new_response = RestApiResponse(
                500,
                {"detail": "Unable to connect the server. Connection error"}
            )
        else:
            content_type = response.headers.get("Content-Type")
            if content_type == "application/json":
                try:
                    new_response = RestApiResponse(
                        response.status_code,
                        response.json(),
                        headers=response.headers,
                    )
                except JSONDecodeError:
                    new_response = RestApiResponse(
                        500,
                        {
                            "detail": "The response is not a JSON: {}".format(
                                response.text)
                        }
                    )

            elif content_type in ("image/jpeg", "image/png"):
                new_response = RestApiResponse(
                    response.status_code,
                    headers=response.headers,
                    content=response.content
                )

            else:
                new_response = RestApiResponse(
                    response.status_code,
                    headers=response.headers,
                )

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

    def query_graphql(self, query, variables=None):
        data = {"query": query, "variables": variables or {}}
        response = self._do_rest_request(
            RequestTypes.post,
            self._graphl_url,
            json=data
        )
        return GraphQlResponse(response)

    def get_graphql_schema(self):
        return self.query_graphql(INTROSPECTION_QUERY).data

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

    def get_all_fields_for_type(self, entity_type):
        attributes = self.get_attributes_for_type(entity_type)
        if entity_type == "project":
            return DEFAULT_PROJECT_FIELDS | {
                "attrib.{}".format(attr)
                for attr in attributes
            }

        if entity_type == "folder":
            return DEFAULT_FOLDER_FIELDS | {
                "attrib.{}".format(attr)
                for attr in attributes
            }

        if entity_type == "task":
            return DEFAULT_TASK_FIELDS | {
                "attrib.{}".format(attr)
                for attr in attributes
            }

        if entity_type == "subset":
            return DEFAULT_SUBSET_FIELDS | {
                "attrib.{}".format(attr)
                for attr in attributes
            }

        if entity_type == "version":
            return DEFAULT_VERSION_FIELDS | {
                "attrib.{}".format(attr)
                for attr in attributes
            }

        if entity_type == "representation":
            return (
                DEFAULT_REPRESENTATION_FIELDS
                | REPRESENTATION_FILES_FIELDS
                | {
                    "attrib.{}".format(attr)
                    for attr in attributes
                }
            )

    # Anatomy presets
    def get_project_anatomy_presets(self, add_default=True):
        result = self.get("anatomy/presets")
        presets = result.data
        if add_default:
            presets.append(self.get_project_anatomy_preset())
        return presets

    def get_project_anatomy_preset(self, preset_name=None):
        if preset_name is None:
            preset_name = "_"
        result = self.get("anatomy/presets/{}".format(preset_name))
        return result.data

    # Settings getters
    def get_full_project_settings(self, project_name):
        result = self.get("projects/{}/settings".format(project_name))
        if result.status == 200:
            return result.data
        return None

    def get_project_settings(self, project_name):
        full_settings = self.get_full_project_settings(project_name)
        if full_settings is None:
            return full_settings
        return full_settings["settings"]

    def get_addon_settings(self, addon_name, addon_version, project_name):
        result = self.get(
            "addons/{}/{}/settings/{}".format(
                addon_name, addon_version, project_name))
        if result.status == 200:
            return result.data
        return None

    # Entity getters
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

    def get_rest_projects(self, active=True, library=None):
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

    def get_project_names(self, active=True, library=None):
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

    def get_projects(self, active=True, library=None, fields=None):
        """Get projects.

        Args:
            active (Union[bool, None]): Filter active or inactive projects.
                Filter is disabled when 'None' is passed.
            library (Union[bool, None]): Filter library projects. Filter is
                disabled when 'None' is passed.
            fields (Union[Iterable[str], None]): fields to be queried
                for project.

        Returns:
            List[Dict[str, Any]]: List of queried projects.
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
                yield project

        else:
            query = projects_graphql_query(fields)
            for parsed_data in query.continuous_query(self):
                for project in parsed_data["projects"]:
                    yield project

    def get_project(self, project_name, fields=None):
        """Get project.

        Args:
            project_name (str): Name of project.
            fields (Union[Iterable[str], None]): fields to be queried
                for project.

        Returns:
            Union[Dict[str, Any], None]: Project entity data or None
                if project was not found.
        """

        use_rest = True
        if fields is not None:
            use_rest = False
            _fields = set()
            for field in fields:
                if field.startswith("config"):
                    use_rest = True
                    break
                _fields.add(field)

            fields = _fields

        if use_rest:
            return self.get_rest_project(project_name)

        query = project_graphql_query(fields)
        query.set_variable_value("projectName", project_name)

        parsed_data = query.query(self)

        data = parsed_data["project"]
        if data is not None:
            data["name"] = project_name
        return data

    def get_folders(
        self,
        project_name,
        folder_ids=None,
        folder_paths=None,
        folder_names=None,
        parent_ids=None,
        active=True,
        fields=None
    ):
        """Query folders from server.

        Todos:
            Folder name won't be unique identifier so we should add folder path
                filtering.

        Notes:
            Filter 'active' don't have direct filter in GraphQl.

        Args:
            folder_ids (Iterable[str]): Folder ids to filter.
            folder_paths (Iterable[str]): Folder paths used for filtering.
            folder_names (Iterable[str]): Folder names used for filtering.
            parent_ids (Iterable[str]): Ids of folder parents. Use 'None'
                if folder is direct child of project.
            active (Union[bool, None]): Filter active/inactive folders.
                Both are returned if is set to None.
            fields (Union[Iterable[str], None]): Fields to be queried for
                folder. All possible folder fields are returned
                if 'None' is passed.

        Returns:
            Iterable[dict[str, Any]]: Queried folder entities.
        """

        if not project_name:
            return []

        filters = {
            "projectName": project_name
        }
        if folder_ids is not None:
            folder_ids = set(folder_ids)
            if not folder_ids:
                return []
            filters["folderIds"] = list(folder_ids)

        if folder_paths is not None:
            folder_paths = set(folder_paths)
            if not folder_paths:
                return []
            filters["folderPaths"] = list(folder_paths)

        if folder_names is not None:
            folder_names = set(folder_names)
            if not folder_names:
                return []
            filters["folderNames"] = list(folder_names)

        if parent_ids is not None:
            parent_ids = set(parent_ids)
            if not parent_ids:
                return []
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

        if fields:
            fields = set(fields)
        else:
            fields = self.get_all_fields_for_type("folder")

        if active is not None:
            fields.add("active")

        query = folders_graphql_query(fields)
        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        for parsed_data in query.continuous_query(self):
            for folder in parsed_data["project"]["folders"]:
                if active is None or active is folder["active"]:
                    yield folder

    def get_tasks(
        self,
        project_name,
        task_ids=None,
        task_names=None,
        task_types=None,
        folder_ids=None,
        active=True,
        fields=None
    ):
        if not project_name:
            return []

        filters = {
            "projectName": project_name
        }

        if task_ids is not None:
            task_ids = set(task_ids)
            if not task_ids:
                return []
            filters["taskIds"] = list(task_ids)

        if task_names is not None:
            task_names = set(task_names)
            if not task_names:
                return []
            filters["taskNames"] = list(task_names)

        if task_types is not None:
            task_types = set(task_types)
            if not task_types:
                return []
            filters["taskTypes"] = list(task_types)

        if folder_ids is not None:
            folder_ids = set(folder_ids)
            if not folder_ids:
                return []
            filters["folderIds"] = list(folder_ids)

        if not fields:
            fields = self.get_all_fields_for_type("task")

        fields = set(fields)
        if active is not None:
            fields.add("active")

        query = tasks_graphql_query(fields)
        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        for parsed_data in query.continuous_query(self):
            for task in parsed_data["project"]["tasks"]:
                if active is None or active is task["active"]:
                    yield task

    def get_task_by_name(
        self, project_name, folder_id, task_name, fields=None
    ):
        for task in self.get_tasks(
            project_name,
            folder_ids=[folder_id],
            task_names=[task_name],
            active=None,
            fields=fields
        ):
            return task
        return None

    def get_task_by_id(self, project_name, task_id, fields=None):
        for task in self.get_tasks(
            project_name,
            task_ids=[task_id],
            active=None,
            fields=fields
        ):
            return task
        return None

    def get_folders_with_tasks(
        self,
        project_name,
        folder_ids=None,
        folder_paths=None,
        folder_names=None,
        parent_ids=None,
        active=True,
        fields=None
    ):
        """Query folders with tasks from server.

        This is for v4 compatibility where tasks were stored on assets. This is
        inefficient way how folders and tasks are queried so it was added only
        as compatibility function.

        Todos:
            Folder name won't be unique identifier so we should add folder path
                filtering.

        Notes:
            Filter 'active' don't have direct filter in GraphQl.

        Args:
            folder_ids (Iterable[str]): Folder ids to filter.
            folder_paths (Iterable[str]): Folder paths used for filtering.
            folder_names (Iterable[str]): Folder names used for filtering.
            parent_ids (Iterable[str]): Ids of folder parents. Use 'None'
                if folder is direct child of project.
            active (Union[bool, None]): Filter active/inactive folders. Both
                are returned if is set to None.
            fields (Union[Iterable(str), None]): Fields to be queried
                for folder. All possible folder fields are returned if 'None'
                is passed.

        Returns:
            List[Dict[str, Any]]: Queried folder entities.
        """

        if not project_name:
            return []

        filters = {
            "projectName": project_name
        }
        if folder_ids is not None:
            folder_ids = set(folder_ids)
            if not folder_ids:
                return []
            filters["folderIds"] = list(folder_ids)

        if folder_paths is not None:
            folder_paths = set(folder_paths)
            if not folder_paths:
                return []
            filters["folderPaths"] = list(folder_paths)

        if folder_names is not None:
            folder_names = set(folder_names)
            if not folder_names:
                return []
            filters["folderNames"] = list(folder_names)

        if parent_ids is not None:
            parent_ids = set(parent_ids)
            if not parent_ids:
                return []
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

        if fields:
            fields = set(fields)
        else:
            fields = self.get_all_fields_for_type("folder")

        if active is not None:
            fields.add("active")

        query = folders_tasks_graphql_query(fields)
        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        parsed_data = query.query(self)
        folders = parsed_data["project"]["folders"]
        if active is None:
            return folders
        return [
            folder
            for folder in folders
            if folder["active"] is active
        ]

    def get_folder_by_id(self, project_name, folder_id, fields=None):
        """Receive folder data by it's id.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            folder_id (str): Folder's id.
            fields (Iterable[str]): Fields that should be returned. All fields
                are returned if 'None' is passed.

        Returns:
            Union[dict, None]: Folder entity data or None if was not found.
        """

        folders = self.get_folders(
            project_name,
            folder_ids=[folder_id],
            active=None,
            fields=fields
        )
        for folder in folders:
            return folder
        return None

    def get_folder_by_path(self, project_name, folder_path, fields=None):
        folders = self.get_folders(
            project_name,
            folder_paths=[folder_path],
            active=None,
            fields=fields
        )
        for folder in folders:
            return folder
        return None

    def get_folder_by_name(self, project_name, folder_name, fields=None):
        folders = self.get_folders(
            project_name,
            folder_names=[folder_name],
            active=None,
            fields=fields
        )
        for folder in folders:
            return folder
        return None

    def get_folder_ids_with_subsets(self, project_name, folder_ids=None):
        if folder_ids is not None:
            folder_ids = set(folder_ids)
            if not folder_ids:
                return set()

        query = folders_graphql_query({"id"})
        query.set_variable_value("projectName", project_name)
        query.set_variable_value("folderHasSubsets", True)
        if folder_ids:
            query.set_variable_value("folderIds", list(folder_ids))

        parsed_data = query.query(self)
        folders = parsed_data["project"]["folders"]
        return {
            folder["id"]
            for folder in folders
        }

    def get_subsets(
        self,
        project_name,
        subset_ids=None,
        subset_names=None,
        folder_ids=None,
        names_by_folder_ids=None,
        active=True,
        fields=None
    ):
        if not project_name:
            return []

        if subset_ids is not None:
            subset_ids = set(subset_ids)
            if not subset_ids:
                return []

        filter_subset_names = None
        if subset_names is not None:
            filter_subset_names = set(subset_names)
            if not filter_subset_names:
                return []

        filter_folder_ids = None
        if folder_ids is not None:
            filter_folder_ids = set(folder_ids)
            if not filter_folder_ids:
                return []

        # This will disable 'folder_ids' and 'subset_names' filters
        #   - maybe could be enhanced in future?
        if names_by_folder_ids is not None:
            filter_subset_names = set()
            filter_folder_ids = set()

            for folder_id, names in names_by_folder_ids.items():
                if folder_id and names:
                    filter_folder_ids.add(folder_id)
                    filter_subset_names |= set(names)

            if not filter_subset_names or not filter_folder_ids:
                return []

        # Convert fields and add minimum required fields
        if fields:
            fields = set(fields) | {"id"}
        else:
            fields = self.get_all_fields_for_type("subset")

        if active is not None:
            fields.add("active")

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

        if subset_ids:
            filters["subsetIds"] = list(subset_ids)

        if filter_subset_names:
            filters["subsetNames"] = list(filter_subset_names)

        query = subsets_graphql_query(fields)
        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        parsed_data = query.query(self)

        subsets = parsed_data.get("project", {}).get("subsets", [])
        if active is not None:
            subsets = [
                subset
                for subset in subsets
                if subset["active"] is active
            ]

        # Filter subsets by 'names_by_folder_ids'
        if names_by_folder_ids:
            subsets_by_folder_id = collections.defaultdict(list)
            for subset in subsets:
                folder_id = subset["folderId"]
                subsets_by_folder_id[folder_id].append(subset)

            filtered_subsets = []
            for folder_id, names in names_by_folder_ids.items():
                for folder_subset in subsets_by_folder_id[folder_id]:
                    if folder_subset["name"] in names:
                        filtered_subsets.append(subset)
            subsets = filtered_subsets

        return list(subsets)

    def get_subset_by_id(self, project_name, subset_id, fields=None):
        subsets = self.get_subsets(
            project_name,
            subset_ids=[subset_id],
            active=None,
            fields=fields
        )
        for subset in subsets:
            return subset
        return None

    def get_subset_by_name(
        self, project_name, subset_name, folder_id, fields=None
    ):
        subsets = self.get_subsets(
            project_name,
            subset_names=[subset_name],
            folder_ids=[folder_id],
            active=None,
            fields=fields
        )
        for subset in subsets:
            return subset
        return None

    def get_subset_families(self, project_name, subset_ids=None):
        if subset_ids is not None:
            subsets = self.get_subsets(
                project_name,
                subset_ids=subset_ids,
                fields=["data.family"],
                active=None,
            )
            return {
                subset["data"]["family"]
                for subset in subsets
            }

        query = GraphQlQuery("SubsetFamilies")
        project_name_var = query.add_variable(
            "projectName", "String!", project_name
        )
        project_query = query.add_field("project")
        project_query.set_filter("name", project_name_var)
        project_query.add_field("subsetFamilies")

        parsed_data = query.query(self)

        return set(parsed_data.get("project", {}).get("subsetFamilies", []))

    def get_versions(
        self,
        project_name,
        version_ids=None,
        subset_ids=None,
        versions=None,
        hero=True,
        standard=True,
        latest=None,
        active=True,
        fields=None
    ):
        """Get version entities based on passed filters from server.

        Args:
            project_name (str): Name of project where to look for versions.
            version_ids (Iterable[str]): Version ids used for version
                filtering.
            subset_ids (Iterable[str]): Subset ids used for version filtering.
            versions (Iterable[int]): Versions we're interested in.
            hero (bool): Receive also hero versions when set to true.
            standard (bool): Receive versions which are not hero when
                set to true.
            latest (bool): Return only latest version of standard versions.
                This can be combined only with 'standard' attribute
                set to True.
            fields (Union[Iterable[str], None]): Fields to be queried
                for version. All possible folder fields are returned
                if 'None' is passed.

        Returns:
            List[Dict[str, Any]]: Queried version entities.
        """

        if not fields:
            fields = self.get_all_fields_for_type("version")
        fields = set(fields)

        if active is not None:
            fields.add("active")

        # Make sure fields have minimum required fields
        fields |= {"id", "version"}

        filters = {
            "projectName": project_name
        }
        if version_ids is not None:
            version_ids = set(version_ids)
            if not version_ids:
                return []
            filters["versionIds"] = list(version_ids)

        if subset_ids is not None:
            subset_ids = set(subset_ids)
            if not subset_ids:
                return []
            filters["subsetIds"] = list(subset_ids)

        # TODO versions can't be used as fitler at this moment!
        if versions is not None:
            versions = set(versions)
            if not versions:
                return []
            filters["versions"] = list(versions)

        if not hero and not standard:
            return []

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

                    yield version

    def get_version_by_id(self, project_name, version_id, fields=None):
        versions = self.get_versions(
            project_name,
            version_ids=[version_id],
            fields=fields,
            active=None,
            hero=True
        )
        for version in versions:
            return version
        return None

    def get_version_by_name(
        self, project_name, version, subset_id, fields=None
    ):
        versions = self.get_versions(
            project_name,
            subset_ids=[subset_id],
            versions=[version],
            active=None,
            fields=fields
        )
        for version in versions:
            return version
        return None

    def get_hero_version_by_id(self, project_name, version_id, fields=None):
        versions = self.get_hero_versions(
            project_name,
            version_ids=[version_id],
            fields=fields
        )
        for version in versions:
            return version
        return None

    def get_hero_version_by_subset_id(
        self, project_name, subset_id, fields=None
    ):
        versions = self.get_hero_versions(
            project_name,
            subset_ids=[subset_id],
            fields=fields
        )
        for version in versions:
            return version
        return None

    def get_hero_versions(
        self,
        project_name,
        subset_ids=None,
        version_ids=None,
        active=True,
        fields=None
    ):
        return self.get_versions(
            project_name,
            version_ids=version_ids,
            subset_ids=subset_ids,
            hero=True,
            standard=False,
            active=active,
            fields=fields
        )

    def get_last_versions(
        self, project_name, subset_ids, active=True, fields=None
    ):
        versions = self.get_versions(
            project_name,
            subset_ids=subset_ids,
            latest=True,
            active=active,
            fields=fields
        )
        return {
            version["parent"]: version
            for version in versions
        }

    def get_last_version_by_subset_id(
        self, project_name, subset_id, active=True, fields=None
    ):
        versions = self.get_versions(
            project_name,
            subset_ids=[subset_id],
            latest=True,
            active=active,
            fields=fields
        )
        for version in versions:
            return version
        return None

    def get_last_version_by_subset_name(
        self, project_name, subset_name, folder_id, active=True, fields=None
    ):
        if not folder_id:
            return None

        subset = self.get_subset_by_name(
            project_name, subset_name, folder_id, fields=["_id"]
        )
        if not subset:
            return None
        return self.get_last_version_by_subset_id(
            project_name, subset["id"], active=active, fields=fields
        )

    def version_is_latest(self, project_name, version_id):
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
        subset_query = version_query.add_field("subset")
        latest_version_query = subset_query.add_field("latestVersion")
        latest_version_query.add_field("id")

        parsed_data = query.query(self)
        latest_version = (
            parsed_data["project"]["version"]["subset"]["latestVersion"]
        )
        return latest_version["id"] == version_id

    def get_representations(
        self,
        project_name,
        representation_ids=None,
        representation_names=None,
        version_ids=None,
        names_by_version_ids=None,
        active=True,
        fields=None
    ):
        """Get version entities based on passed filters from server.

        Todo:
            Add separated function for 'names_by_version_ids' filtering.
                Because can't be combined with others.

        Args:
            project_name (str): Name of project where to look for versions.
            representation_ids (Iterable[str]): Representaion ids used for
                representation filtering.
            representation_names (Iterable[str]): Representation names used for
                representation filtering.
            version_ids (Iterable[str]): Version ids used for
                representation filtering. Versions are parents of
                    representations.
            names_by_version_ids (bool): Find representations by names and
                version ids. This filter discard all other filters.
            active (bool): Receive active/inactive representaions. All are
                returned when 'None' is passed.
            fields (Union[Iterable[str], None]): Fields to be queried for
                representation. All possible fields are returned if 'None' is
                passed.

        Returns:
            List[Dict[str, Any]]: Queried representation entities.
        """

        if not fields:
            fields = self.get_all_fields_for_type("representation")
        fields = set(fields)

        if active is not None:
            fields.add("active")

        filters = {
            "projectName": project_name
        }

        if representation_ids is not None:
            representation_ids = set(representation_ids)
            if not representation_ids:
                return []
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
                return []

        else:
            if representation_names is not None:
                representaion_names_filter = set(representation_names)
                if not representaion_names_filter:
                    return []

            if version_ids is not None:
                version_ids_filter = set(version_ids)
                if not version_ids_filter:
                    return []

        if version_ids_filter:
            filters["versionIds"] = list(version_ids_filter)

        if representaion_names_filter:
            filters["representationNames"] = list(representaion_names_filter)

        query = representations_graphql_query(fields)

        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        for parsed_data in query.continuous_query(self):
            for repre in parsed_data["project"]["representations"]:
                if active is None or active is repre["active"]:
                    if "context" in repre:
                        orig_context = repre["context"]
                        context = {}
                        if orig_context and orig_context != "null":
                            context = json.loads(orig_context)
                        repre["context"] = context
                    yield repre

    def get_representation_by_id(
        self, project_name, representation_id, fields=None
    ):
        representations = self.get_representations(
            project_name,
            representation_ids=[representation_id],
            active=None,
            fields=fields,
        )
        for representation in representations:
            return representation
        return None

    def get_representation_by_name(
        self, project_name, representation_name, version_id, fields=None
    ):
        representations = self.get_representations(
            project_name,
            representation_names=[representation_name],
            version_ids=[version_id],
            active=None,
            fields=fields,
        )
        for representation in representations:
            return representation
        return None

    def get_representation_parents(self, project_name, representation):
        if not representation:
            return None

        repre_id = representation["_id"]
        parents_by_repre_id = self.get_representations_parents(
            project_name, [representation]
        )
        return parents_by_repre_id[repre_id]

    def get_representations_parents(self, project_name, representation_ids):
        if not representation_ids:
            return {}

        project = self.get_project(project_name)
        repre_ids = set(representation_ids)
        output = {
            repre_id: (None, None, None, None)
            for repre_id in representation_ids
        }

        version_fields = self.get_all_fields_for_type("version")
        subset_fields = self.get_all_fields_for_type("subset")
        folder_fields = self.get_all_fields_for_type("folder")

        query = representations_parents_qraphql_query(
            version_fields, subset_fields, folder_fields
        )
        query.set_variable_value("projectName", project_name)
        query.set_variable_value("representationIds", list(repre_ids))

        parsed_data = query.query(self)
        for repre in parsed_data["project"]["representations"]:
            repre_id = repre["id"]
            version = repre.pop("version")
            subset = version.pop("subset")
            folder = subset.pop("folder")
            output[repre_id] = (version, subset, folder, project)

        return output

    def get_thumbnail_id_from_source(self, project_name, src_type, src_id):
        """Receive thumbnail id from source entity.

        Args:
            project_name (str): Name of project where to look for queried
                entities.
            src_type (str): Type of source entity ('folder', 'version').
            src_id (Union[str, ObjectId]): Id of source entity.

        Returns:
            ObjectId: Thumbnail id assigned to entity.
            None: If Source entity does not have any thumbnail id assigned.
        """

        if not src_type or not src_id:
            return None

        if src_type == "subset":
            subset = self.get_subset_by_id(
                project_name, src_id, fields=["data.thumbnail_id"]
            ) or {}
            return subset.get("data", {}).get("thumbnail_id")

        if src_type == "folder":
            subset = self.get_folder_by_id(
                project_name, src_id, fields=["data.thumbnail_id"]
            ) or {}
            return subset.get("data", {}).get("thumbnail_id")

        return None

    def get_workfiles_info(
        self,
        project_name,
        workfile_ids=None,
        task_ids=None,
        paths=None,
        fields=None
    ):
        filters = {}
        if task_ids is not None:
            task_ids = set(task_ids)
            if not task_ids:
                return []
            filters["taskIds"] = list(task_ids)

        if paths is not None:
            paths = set(paths)
            if not paths:
                return []
            filters["paths"] = list(paths)

        if workfile_ids is not None:
            workfile_ids = set(workfile_ids)
            if not workfile_ids:
                return []
            filters["workfileIds"] = list(workfile_ids)

        if not fields:
            fields = DEFAULT_WORKFILE_INFO_FIELDS
        fields = set(fields)

        query = workfiles_info_graphql_query()

        for attr, filter_value in filters.items():
            query.set_variable_value(attr, filter_value)

        for parsed_data in query.continuous_query(self):
            for workfile_info in parsed_data["project"]["workfiles"]:
                yield workfile_info

    def get_workfile_info(
        self, project_name, task_id, path, fields=None
    ):
        if not task_id or not path:
            return None

        for workfile_info in self.get_workfiles_info(
            project_name,
            task_ids=[task_id],
            paths=[path],
            fields=fields
        ):
            return workfile_info
        return None

    def get_workfile_info_by_id(
        self, project_name, workfile_id, fields=None
    ):
        if not workfile_id:
            return None

        for workfile_info in self.get_workfiles_info(
            project_name,
            workfile_ids=[workfile_id],
            fields=fields
        ):
            return workfile_info
        return None
