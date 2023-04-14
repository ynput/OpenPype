import copy


class UrlError(Exception):
    """Url cannot be parsed as url.

    Exception may contain hints of possible fixes of url that can be used in
    UI if needed.
    """

    def __init__(self, message, title, hints=None):
        if hints is None:
            hints = []

        self.title = title
        self.hints = hints
        super(UrlError, self).__init__(message)


class ServerError(Exception):
    pass


class UnauthorizedError(ServerError):
    pass


class AuthenticationError(ServerError):
    pass


class ServerNotReached(ServerError):
    pass


class RequestError(Exception):
    def __init__(self, message, response):
        self.response = response
        super(RequestError, self).__init__(message)


class HTTPRequestError(RequestError):
    pass


class GraphQlQueryFailed(Exception):
    def __init__(self, errors, query, variables):
        if variables is None:
            variables = {}

        error_messages = []
        for error in errors:
            msg = error["message"]
            path = error.get("path")
            if path:
                msg += " on item '{}'".format("/".join(path))
            locations = error.get("locations")
            if locations:
                _locations = [
                    "Line {} Column {}".format(
                        location["line"], location["column"]
                    )
                    for location in locations
                ]

                msg += " ({})".format(" and ".join(_locations))
            error_messages.append(msg)

        message = "GraphQl query Failed"
        if error_messages:
            message = "{}: {}".format(message, " | ".join(error_messages))

        self.errors = errors
        self.query = query
        self.variables = copy.deepcopy(variables)
        super(GraphQlQueryFailed, self).__init__(message)


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


class FailedOperations(Exception):
    pass


class FailedServiceInit(Exception):
    pass
