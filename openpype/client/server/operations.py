import re
from openpype.client.operations_base import BaseOperationsSession


PROJECT_NAME_ALLOWED_SYMBOLS = "a-zA-Z0-9_"
PROJECT_NAME_REGEX = re.compile(
    "^[{}]+$".format(PROJECT_NAME_ALLOWED_SYMBOLS)
)


class OperationsSession(BaseOperationsSession):
    def commit(self):
        raise NotImplementedError(
            "{} dose not have implemented 'commit'".format(
                self.__class__.__name__))


def create_project(project_name, project_code, library_project=False):
    """Create project using OpenPype settings.

    This project creation function is not validating project document on
    creation. It is because project document is created blindly with only
    minimum required information about project which is it's name, code, type
    and schema.

    Entered project name must be unique and project must not exist yet.

    Note:
        This function is here to be OP v4 ready but in v3 has more logic
            to do. That's why inner imports are in the body.

    Args:
        project_name (str): New project name. Should be unique.
        project_code (str): Project's code should be unique too.
        library_project (bool): Project is library project.
        con (ServerAPI): Connection to server with logged user.

    Raises:
        ValueError: When project name already exists in MongoDB.

    Returns:
        dict: Created project document.
    """

    if get_project(project_name, fields=["name"]):
        raise ValueError("Project with name \"{}\" already exists".format(
            project_name
        ))

    if not PROJECT_NAME_REGEX.match(project_name):
        raise ValueError((
            "Project name \"{}\" contain invalid characters"
        ).format(project_name))

    if con is None:
        con = get_server_api_connection()

    result = con.put(
        "projects/{}".format(project_name),
        code=project_code,
        library=library_project
    )
    if result.status != 201:
        details = "Unknown details ({})".format(result.status)
        if result.data:
            details = result.data.get("detail") or details
        raise ValueError("Failed to create project \"{}\": {}".format(
            project_name, details
        ))

    return get_project(project_name)
