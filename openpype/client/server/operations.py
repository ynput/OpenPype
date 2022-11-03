import re
import uuid
import copy
import json
import collections

from openpype.client.operations_base import (
    REMOVED_VALUE,
    CreateOperation,
    UpdateOperation,
    DeleteOperation,
    BaseOperationsSession
)

from .server import get_server_api_connection
from .entities import get_project, get_v4_project_anatomy_preset
from .conversion_utils import (
    convert_create_asset_to_v4,
    convert_create_task_to_v4,
    convert_create_subset_to_v4,
    convert_create_version_to_v4,
    convert_create_representation_to_v4,

    convert_update_folder_to_v4,
    convert_update_subset_to_v4,
    convert_update_version_to_v4,
    convert_update_representation_to_v4,
)


PROJECT_NAME_ALLOWED_SYMBOLS = "a-zA-Z0-9_"
PROJECT_NAME_REGEX = re.compile(
    "^[{}]+$".format(PROJECT_NAME_ALLOWED_SYMBOLS)
)


class OperationsSession(BaseOperationsSession):
    def commit(self):
        raise NotImplementedError(
            "{} dose not have implemented 'commit'".format(
                self.__class__.__name__))


def create_project(
    project_name,
    project_code,
    library_project=False,
    preset_name=None,
    con=None
):
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
        preset_name (str): Name of anatomy preset. Default is used if not
            passed.
        con (ServerAPI): Connection to server with logged user.

    Raises:
        ValueError: When project name already exists in MongoDB.

    Returns:
        dict: Created project document.
    """

    if con is None:
        con = get_server_api_connection()

    if get_project(project_name, fields=["name"], con=con):
        raise ValueError("Project with name \"{}\" already exists".format(
            project_name
        ))

    if not PROJECT_NAME_REGEX.match(project_name):
        raise ValueError((
            "Project name \"{}\" contain invalid characters"
        ).format(project_name))

    preset = get_v4_project_anatomy_preset(preset_name)
    config = {
        "templates": preset["templates"],
        "roots": preset["roots"]
    }
    folder_types = {}
    for folder_type in preset["folder_types"]:
        name = folder_type.pop("name")
        folder_types[name] = folder_type

    task_types = {}
    for task_type in preset["task_types"]:
        name = task_type.pop("name")
        task_types[name] = task_type

    result = con.put(
        "projects/{}".format(project_name),
        code=project_code,
        library=library_project,
        config=config,
        attrib=preset["attributes"],
        folderTypes=folder_types,
        taskTypes=task_types
    )
    if result.status != 201:
        details = "Unknown details ({})".format(result.status)
        if result.data:
            details = result.data.get("detail") or details
        raise ValueError("Failed to create project \"{}\": {}".format(
            project_name, details
        ))

    return get_project(project_name)


def delete_project(project_name, con=None):
    if con is None:
        con = get_server_api_connection()

    if not get_project(project_name, fields=["name"], con=con):
        raise ValueError("Project with name \"{}\" was not found".format(
            project_name
        ))

    result = con.delete("projects/{}".format(project_name))
    if result.status_code != 204:
        raise ValueError(
            "Failed to delete project \"{}\". {}".format(
                project_name, result.data["detail"]
            )
        )
