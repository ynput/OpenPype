import collections
import datetime

from .constants import (
    FOLDER_ATTRIBS,
    DEFAULT_V3_FOLDER_FIELDS,
    DEFAULT_FOLDER_FIELDS,
    FOLDER_ATTRIBS_FIELDS,

    SUBSET_ATTRIBS,
    DEFAULT_SUBSET_FIELDS,

    VERSION_ATTRIBS_FIELDS,
    DEFAULT_VERSION_FIELDS,

    REPRESENTATION_ATTRIBS_FIELDS,
    REPRESENTATION_FILES_FIELDS,
    DEFAULT_REPRESENTATION_FIELDS,
)
from .graphql import GraphQlQuery
from .graphql_queries import (
    project_graphql_query,
    projects_graphql_query,
    folders_graphql_query,
    tasks_graphql_query,
    folders_tasks_graphql_query,
    subsets_graphql_query,
    versions_graphql_query,
    representations_graphql_query,
    reprersentations_parents_qraphql_query,
)
from .server import get_server_api_connection


# --- Project entity ---
PROJECT_FIELDS_MAPPING_V3_V4 = {
    "_id": {"name"},
    "name": {"name"},
    "data": {"data", "attrib", "code"},
    "data.library_project": {"library"},
    "data.code": {"code"},
    "data.active": {"active"},
}

# TODO this should not be hardcoded but received from server!!!
# --- Folder entity ---
FOLDER_FIELDS_MAPPING_V3_V4 = {
    "_id": {"id"},
    "name": {"name"},
    "label": {"name"},
    "data": {
        "parentId", "parents", "active", "tasks", "thumbnailId"
    } | FOLDER_ATTRIBS_FIELDS,
    "data.visualParent": {"parentId"},
    "data.parents": {"parents"},
    "data.active": {"active"},
    "data.thumbnail_id": {"thumbnailId"}
}

# --- Subset entity ---
SUBSET_FIELDS_MAPPING_V3_V4 = {
    "_id": {"id"},
    "name": {"name"},
    "data.active": {"active"},
    "parent": {"folderId"}
}

# --- Version entity ---
VERSION_FIELDS_MAPPING_V3_V4 = {
    "_id": {"id"},
    "name": {"version"},
    "parent": {"subsetId"}
}

# --- Representation entity ---
REPRESENTATION_FIELDS_MAPPING_V3_V4 = {
    "_id": {"id"},
    "name": {"name"},
    "parent": {"versionId"},
    "context": {"context"},
    "files": {"files"},
}

# CURRENT_PROJECT_CONFIG_SCHEMA = "openpype:config-2.0"
# CURRENT_WORKFILE_INFO_SCHEMA = "openpype:workfile-1.0"
# CURRENT_THUMBNAIL_SCHEMA = "openpype:thumbnail-1.0"


def _project_fields_v3_to_v4(fields):
    """Convert project fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    # TODO config fields
    # - config.apps
    # - config.groups
    if not fields:
        return None

    output = set()
    for field in fields:
        # If config is needed the rest api call must be used
        if field.startswith("config"):
            return None

        if field in PROJECT_FIELDS_MAPPING_V3_V4:
            output |= PROJECT_FIELDS_MAPPING_V3_V4[field]

        elif field.startswith("data"):
            new_field = "attrib" + field[4:]
            output.add(new_field)

        else:
            raise ValueError("Unknown field mapping for {}".format(field))

    if "name" not in output:
        output.add("name")
    return output


def _convert_v4_project_to_v3(project):
    """Convert Project entity data from v4 structure to v3 structure.

    Args:
        project (Dict[str, Any]): Project entity queried from v4 server.

    Returns:
        Dict[str, Any]: Project converted to v3 structure.
    """

    if not project:
        return project

    project_name = project["name"]
    output = {
        "_id": project_name,
        "name": project_name,
        "schema": "openpype:project-3.0"
    }
    if "config" in project:
        output["config"] = project["config"]
        output["config"]["tasks"] = project.get("taskTypes")
        output["config"]["apps"] = []

    data = project.get("data") or {}

    for data_key, key in (
        ("library_project", "library"),
        ("code", "code"),
        ("active", "active")
    ):
        if key in project:
            data[data_key] = project[key]

    if "attrib" in project:
        for key, value in project["attrib"].items():
            data[key] = value

    if data:
        output["data"] = data
    return output


def _folder_fields_v3_to_v4(fields):
    """Convert folder fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    if not fields:
        return set(DEFAULT_V3_FOLDER_FIELDS)

    output = set()
    for field in fields:
        if field in ("schema", "type", "parent"):
            continue

        if field in FOLDER_FIELDS_MAPPING_V3_V4:
            output |= FOLDER_FIELDS_MAPPING_V3_V4[field]

        elif field.startswith("data"):
            field_parts = field.split(".")
            field_parts.pop(0)
            data_key = ".".join(field_parts)
            if data_key == "label":
                output.add("name")

            elif data_key in ("icon", "color"):
                continue

            elif data_key.startswith("tasks"):
                output.add("tasks")
            elif data_key in FOLDER_ATTRIBS:
                new_field = "attrib" + field[4:]
                output.add(new_field)
            else:
                print(data_key)
                raise ValueError("Can't query data for field {}".format(field))

        else:
            raise ValueError("Unknown field mapping for {}".format(field))

    if "id" not in output:
        output.add("id")
    return output


def _convert_v4_tasks_to_v3(tasks):
    """Convert v4 task item to v3 task.

    Args:
        tasks (List[Dict[str, Any]]): Task entites.

    Returns:
        Dict[str, Dict[str, Any]]: Tasks in v3 variant ready for v3 asset.
    """

    output = {}
    for task in tasks:
        task_name = task["name"]
        new_task = {
            "type": task["taskType"]
        }
        output[task_name] = new_task
    return output


def _convert_v4_folder_to_v3(folder, project_name):
    """Convert v4 folder to v3 asset.

    Args:
        folder (Dict[str, Any]): Folder entity data.
        project_name (str): Project name from which folder was queried.

    Returns:
        Dict[str, Any]: Converted v4 folder to v3 asset.
    """

    output = {
        "_id": folder["id"],
        "parent": project_name,
        "type": "asset",
        "schema": "openpype:asset-3.0"
    }

    output_data = folder.get("data") or {}

    if "name" in folder:
        output["name"] = folder["name"]
        output_data["label"] = folder["name"]

    for data_key, key in (
        ("visualParent", "parentId"),
        ("active", "active"),
        ("thumbnail_id", "thumbnailId")
    ):
        if key not in folder:
            continue

        output_data[data_key] = folder[key]

    if "attrib" in folder:
        output_data.update(folder["attrib"])

    if "tasks" in folder:
        if output_data is None:
            output_data = {}
        output_data["tasks"] = _convert_v4_tasks_to_v3(folder["tasks"])

    output["data"] = output_data

    return output


def _subset_fields_v3_to_v4(fields):
    """Convert subset fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    if not fields:
        return None

    output = set()
    for field in fields:
        if field in ("schema", "type"):
            continue

        if field in SUBSET_FIELDS_MAPPING_V3_V4:
            output |= SUBSET_FIELDS_MAPPING_V3_V4[field]

        elif field == "data":
            output.add("family")
            output |= SUBSET_ATTRIBS

        elif field.startswith("data"):
            field_parts = field.split(".")
            field_parts.pop(0)
            data_key = ".".join(field_parts)
            if data_key == "subsetGroup":
                output.add("attrib.subsetGroup")

            elif data_key in ("family", "families"):
                output.add("family")

            else:
                print(data_key)
                raise ValueError("Can't query data for field {}".format(field))

        else:
            raise ValueError("Unknown field mapping for {}".format(field))

    if "id" not in output:
        output.add("id")
    return output


def _convert_v4_subset_to_v3(subset):
    output = {
        "_id": subset["id"],
        "type": "subset",
        "schema": "openpype:subset-3.0"
    }
    if "folderId" in subset:
        output["parent"] = subset["folderId"]

    output_data = subset.get("data") or {}

    if "name" in subset:
        output["name"] = subset["name"]

    if "active" in subset:
        output_data["active"] = subset["active"]

    if "attrib" in subset:
        attrib = subset["attrib"]
        output_data.update(attrib)

    family = subset.get("family")
    if family:
        output_data["family"] = family
        output_data["families"] = [family]

    output["data"] = output_data

    return output


def _version_fields_v3_to_v4(fields):
    """Convert version fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    if not fields:
        return None

    output = set()
    for field in fields:
        if field in ("type", "schema", "version_id"):
            continue

        if field in VERSION_FIELDS_MAPPING_V3_V4:
            output |= VERSION_FIELDS_MAPPING_V3_V4[field]

        elif field == "data":
            output |= VERSION_ATTRIBS_FIELDS
            output |= {
                "author",
                "createdAt",
                "thumbnailId",
            }

        elif field.startswith("data"):
            field_parts = field.split(".")
            field_parts.pop(0)
            data_key = ".".join(field_parts)
            if data_key == "thumbnail_id":
                output.add("thumbnailId")

            elif data_key == "time":
                output.add("createdAt")

            elif data_key == "author":
                output.add("author")

            elif data_key in ("tags", ):
                continue

            else:
                print(data_key)
                raise ValueError("Can't query data for field {}".format(field))

        else:
            raise ValueError("Unknown field mapping for {}".format(field))

    if "id" not in output:
        output.add("id")
    return output


def _convert_v4_version_to_v3(version):
    """Convert v4 version entity to v4 version.

    Args:
        version (Dict[str, Any]): Queried v4 version entity.

    Returns:
        Dict[str, Any]: Conveted version entity to v3 structure.
    """

    version_num = version["version"]
    doc_type = "version"
    schema = "openpype:version-3.0"
    if version_num < 0:
        doc_type = "hero_version"
        schema = "openpype:hero_version-1.0"

    output = {
        "_id": version["id"],
        "type": doc_type,
        "name": version_num,
        "schema": schema
    }
    if "subsetId" in version:
        output["parent"] = version["subsetId"]

    output_data = version.get("data") or {}
    if "attrib" in version:
        output_data.update(version["attrib"])

    for key, data_key in (
        ("active", "active"),
        ("thumbnailId", "thumbnail_id"),
        ("author", "author")
    ):
        if key in version:
            output_data[data_key] = version[key]

    if "createdAt" in version:
        # TODO probably will need a conversion?
        created_at = datetime.datetime.fromtimestamp(version["createdAt"])
        output_data["time"] = created_at.strftime("%Y%m%dT%H%M%SZ")

    output["data"] = output_data

    return output


def _representation_fields_v3_to_v4(fields):
    """Convert representation fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    if not fields:
        return None

    output = set()
    for field in fields:
        if field in ("type", "schema"):
            continue

        if field in REPRESENTATION_FIELDS_MAPPING_V3_V4:
            output |= REPRESENTATION_FIELDS_MAPPING_V3_V4[field]

        elif field.startswith("context"):
            output.add("context")

        # TODO: 'files' can have specific attributes but the keys in v3 and v4
        #   are not the same (content is not the same)
        elif field.startswith("files"):
            output |= REPRESENTATION_FILES_FIELDS

        elif field.startswith("data"):
            fields |= REPRESENTATION_ATTRIBS_FIELDS

        else:
            raise ValueError("Unknown field mapping for {}".format(field))

    if "id" not in output:
        output.add("id")
    return output


def _convert_v4_representation_to_v3(representation):
    """Convert v4 representation to v3 representation.

    Args:
        representation (Dict[str, Any]): Queried representation from v4 server.

    Returns:
        Dict[str, Any]: Converted representation to v3 structure.
    """

    output = {
        "_id": representation["id"],
        "type": "representation",
        "schema": "openpype:representation-2.0",
    }
    for v3_key, v4_key in (
        ("name", "name"),
        ("files", "files"),
        ("context", "context"),
        ("parent", "versionId")
    ):
        if v4_key in representation:
            output[v3_key] = representation[v4_key]

    if "files" in output and not output["files"]:
        # Fake studio files
        output["files"].append({
            "name": "studio",
            "created_dt": datetime.datetime.now()
        })
    output_data = representation.get("data") or {}
    if "attrib" in representation:
        output_data.update(representation["attrib"])

    for key, data_key in (
        ("active", "active"),
    ):
        if key in representation:
            output_data[data_key] = representation[key]

    output["data"] = output_data

    return output


def get_v4_projects(active=None, library=None, fields=None):
    """Get v4 projects.

    Args:
        active (Union[bool, None]): Filter active or inactive projects. Filter
            is disabled when 'None' is passed.
        library (Union[bool, None]): Filter library projects. Filter is
            disabled when 'None' is passed.
        fields (Union[Iterable(str), None]): fields to be queried for project.

    Returns:
        List[Dict[str, Any]]: List of queried projects.
    """

    con = get_server_api_connection()
    if not fields:
        for project in con.get_rest_projects(active, library):
            yield project

    else:
        query = projects_graphql_query(fields)
        for parsed_data in query.continuous_query(con):
            for project in parsed_data["projects"]:
                yield project


def get_v4_project(project_name, fields=None):
    """Get v4 project.

    Args:
        project_name (str): Nameo project.
        fields (Union[Iterable(str), None]): fields to be queried for project.

    Returns:
        Union[Dict[str, Any], None]: Project entity data or None if project was
            not found.
    """

    # Skip if both are disabled
    con = get_server_api_connection()
    if not fields:
        return _convert_v4_project_to_v3(
            con.get_rest_project(project_name)
        )

    fields = set(fields)
    query = project_graphql_query(fields)
    query.set_variable_value("projectName", project_name)

    parsed_data = query.query(con)

    data = parsed_data["project"]
    data["name"] = project_name
    return _convert_v4_project_to_v3(data)


def get_v4_folders(
    project_name,
    folder_ids=None,
    folder_paths=None,
    folder_names=None,
    parent_ids=None,
    active=None,
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
        parent_ids (Iterable[str]): Ids of folder parents. Use 'None' if folder
            is direct child of project.
        active (Union[bool, None]): Filter active/inactive folders. Both are
            returned if is set to None.
        fields (Union[Iterable(str), None]): Fields to be queried for folder.
            All possible folder fields are returned if 'None' is passed.

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
            # Replace 'None' with '"root"' which is used during GraphQl query
            #   for parent ids filter for folders without folder parent
            parent_ids.remove(None)
            parent_ids.add("root")

        if project_name in parent_ids:
            # Replace project name with '"root"' which is used during GraphQl
            #   query for parent ids filter for folders without folder parent
            parent_ids.remove(project_name)
            parent_ids.add("root")

        filters["parentFolderIds"] = list(parent_ids)

    if not fields:
        fields = DEFAULT_FOLDER_FIELDS
    fields = set(fields)
    if active is not None:
        fields.add("active")

    query = folders_graphql_query(fields)
    for attr, filter_value in filters.items():
        query.set_variable_value(attr, filter_value)

    con = get_server_api_connection()
    for parsed_data in query.continuous_query(con):
        for folder in parsed_data["project"]["folders"]:
            if active is None or active is folder["active"]:
                yield folder


def get_v4_tasks(
    project_name,
    task_ids=None,
    task_names=None,
    task_types=None,
    folder_ids=None,
    active=None,
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
        fields = DEFAULT_FOLDER_FIELDS
    fields = set(fields)
    if active is not None:
        fields.add("active")

    query = tasks_graphql_query(fields)
    for attr, filter_value in filters.items():
        query.set_variable_value(attr, filter_value)

    con = get_server_api_connection()
    parsed_data = query.query(con)
    tasks = parsed_data["project"]["tasks"]

    if active is None:
        return tasks
    return [
        task
        for task in tasks
        if task["active"] is active
    ]


def get_v4_folders_tasks(
    project_name,
    folder_ids=None,
    folder_paths=None,
    folder_names=None,
    parent_ids=None,
    active=None,
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
        parent_ids (Iterable[str]): Ids of folder parents. Use 'None' if folder
            is direct child of project.
        active (Union[bool, None]): Filter active/inactive folders. Both are
            returned if is set to None.
        fields (Union[Iterable(str), None]): Fields to be queried for folder.
            All possible folder fields are returned if 'None' is passed.

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
            # Replace 'None' with '"root"' which is used during GraphQl query
            #   for parent ids filter for folders without folder parent
            parent_ids.remove(None)
            parent_ids.add("root")

        if project_name in parent_ids:
            # Replace project name with '"root"' which is used during GraphQl
            #   query for parent ids filter for folders without folder parent
            parent_ids.remove(project_name)
            parent_ids.add("root")

        filters["parentFolderIds"] = list(parent_ids)

    if not fields:
        fields = DEFAULT_V3_FOLDER_FIELDS
    fields = set(fields)
    if active is not None:
        fields.add("active")

    query = folders_tasks_graphql_query(fields)
    for attr, filter_value in filters.items():
        query.set_variable_value(attr, filter_value)

    con = get_server_api_connection()
    parsed_data = query.query(con)
    folders = parsed_data["project"]["folders"]
    if active is None:
        return folders
    return [
        folder
        for folder in folders
        if folder["active"] is active
    ]


def get_v4_versions(
    project_name,
    version_ids=None,
    subset_ids=None,
    versions=None,
    hero=True,
    standard=True,
    latest=None,
    fields=None
):
    """Get version entities based on passed filters from server.

    Args:
        project_name (str): Name of project where to look for versions.
        version_ids (Iterable[str]): Version ids used for version filtering.
        subset_ids (Iterable[str]): Subset ids used for version filtering.
        versions (Iterable[int]): Versions we're interested in.
        hero (bool): Receive also hero versions when set to true.
        standard (bool): Receive versions which are not hero when set to true.
        latest (bool): Return only latest version of standard versions.
            This can be combined only with 'standard' attribute set to True.
        fields (Union[Iterable(str), None]): Fields to be queried for version.
            All possible folder fields are returned if 'None' is passed.

    Returns:
        List[Dict[str, Any]]: Queried version entities.
    """

    if not fields:
        fields = DEFAULT_VERSION_FIELDS
    fields = set(fields)

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

    # Add filters based on 'hero' and 'stadard'
    if hero and not standard:
        filters["heroOnly"] = True
    elif hero and latest:
        filters["heroOrLatestOnly"] = True
    elif latest:
        filters["latestOnly"] = True

    # Make sure fields have minimum required fields
    fields |= {"id", "version"}

    query = versions_graphql_query(fields)

    for attr, filter_value in filters.items():
        query.set_variable_value(attr, filter_value)

    con = get_server_api_connection()
    parsed_data = query.query(con)

    return parsed_data.get("project", {}).get("versions", [])


def get_v4_representations(
    project_name,
    representation_ids=None,
    representation_names=None,
    version_ids=None,
    names_by_version_ids=None,
    active=None,
    fields=None
):
    """Get version entities based on passed filters from server.

    Todo:
        Add separated function for 'names_by_version_ids' filtering. Because
            can't be combined with others.

    Args:
        project_name (str): Name of project where to look for versions.
        representation_ids (Iterable[str]): Representaion ids used for
            representation filtering.
        representation_names (Iterable[str]): Representation names used for
            representation filtering.
        version_ids (Iterable[str]): Version ids used for
            representation filtering. Versions are parents of representations.
        names_by_version_ids (bool): Find representations by names and
            version ids. This filter discard all other filters.
        active (bool): Receive active/inactive representaions. All are returned
            when 'None' is passed.
        fields (Union[Iterable(str), None]): Fields to be queried for
            representation. All possible fields are returned if 'None' is
            passed.

    Returns:
        List[Dict[str, Any]]: Queried representation entities.
    """

    if not fields:
        fields = DEFAULT_REPRESENTATION_FIELDS
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

    con = get_server_api_connection()
    parsed_data = query.query(con)

    representations = parsed_data.get("project", {}).get("representations", [])
    if active is None:
        representations = [
            repre
            for repre in representations
            if repre["active"] == active
        ]
    return representations


def get_projects(active=True, inactive=False, library=None, fields=None):
    if not active and not inactive:
        return []

    if active and inactive:
        active = None
    elif active:
        active = True
    elif inactive:
        active = False

    fields = _project_fields_v3_to_v4(fields)
    for project in get_v4_projects(active, library, fields):
        yield _convert_v4_project_to_v3(project)


def get_project(project_name, active=True, inactive=False, fields=None):
    # Skip if both are disabled
    fields = _project_fields_v3_to_v4(fields)

    return get_v4_project(project_name, fields=fields)


def get_whole_project(*args, **kwargs):
    raise NotImplementedError("'get_whole_project' not implemented")


def _get_subsets(
    project_name,
    subset_ids=None,
    subset_names=None,
    folder_ids=None,
    names_by_folder_ids=None,
    archived=False,
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
    fields = _subset_fields_v3_to_v4(fields)
    if fields is not None:
        for key in (
            "id",
            "active"
        ):
            fields.add(key)

    if fields is None:
        fields = set(DEFAULT_SUBSET_FIELDS)

    # Add 'name' and 'folderId' if 'name_by_asset_ids' filter is entered
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

    con = get_server_api_connection()
    parsed_data = query.query(con)

    subsets = parsed_data.get("project", {}).get("subsets", [])

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

    return [
        _convert_v4_subset_to_v3(subset)
        for subset in subsets
    ]


def _get_versions(
    project_name,
    version_ids=None,
    subset_ids=None,
    versions=None,
    hero=True,
    standard=True,
    latest=None,
    fields=None
):
    fields = _version_fields_v3_to_v4(fields)
    # Make sure 'subsetId' and 'version' are available when hero versions
    #   are queried
    if fields and hero:
        fields = set(fields)
        fields |= {"subsetId", "version"}

    queried_versions = get_v4_versions(
        project_name,
        version_ids,
        subset_ids,
        versions,
        hero,
        standard,
        latest,
        fields
    )

    versions = []
    hero_versions = []
    for version in queried_versions:
        if version["version"] < 0:
            hero_versions.append(version)
        else:
            versions.append(_convert_v4_version_to_v3(version))

    if hero_versions:
        subset_ids = set()
        versions_nums = set()
        for hero_version in hero_versions:
            versions_nums.add(abs(hero_version["version"]))
            subset_ids.add(hero_version["subsetId"])

        hero_eq_versions = get_v4_versions(
            project_name,
            subset_ids=subset_ids,
            versions=versions_nums,
            hero=False,
            fields=["id", "version", "subsetId"],
        )
        hero_eq_by_subset_id = collections.defaultdict(list)
        for version in hero_eq_versions:
            hero_eq_by_subset_id[version["subsetId"]].append(version)

        for hero_version in hero_versions:
            abs_version = abs(hero_version["version"])
            subset_id = hero_version["subsetId"]
            version_id = None
            for version in hero_eq_by_subset_id.get(subset_id, []):
                if version["version"] == abs_version:
                    version_id = version["id"]
                    break
            conv_hero = _convert_v4_version_to_v3(hero_version)
            conv_hero["version_id"] = version_id

    return versions


def get_asset_by_id(project_name, asset_id, fields=None):
    assets = get_assets(project_name, asset_ids=[asset_id], fields=fields)
    for asset in assets:
        return asset
    return None


def get_asset_by_name(project_name, asset_name, fields=None):
    assets = get_assets(project_name, asset_names=[asset_name], fields=fields)
    for asset in assets:
        return asset
    return None


def get_assets(
    project_name,
    asset_ids=None,
    asset_names=None,
    parent_ids=None,
    archived=False,
    fields=None
):
    if not project_name:
        return []

    active = True
    if archived:
        active = False

    fields = _folder_fields_v3_to_v4(fields)
    kwargs = dict(
        folder_ids=asset_ids,
        folder_names=asset_names,
        parent_ids=parent_ids,
        active=active,
        fields=fields
    )
    if "tasks" in fields:
        folders = get_v4_folders_tasks(project_name, **kwargs)
    else:
        folders = get_v4_folders(project_name, **kwargs)

    for folder in folders:
        yield _convert_v4_folder_to_v3(folder, project_name)


def get_archived_assets(*args, **kwargs):
    raise NotImplementedError("'get_archived_assets' not implemented")


def get_asset_ids_with_subsets(project_name, asset_ids=None):
    if asset_ids is not None:
        asset_ids = set(asset_ids)
        if not asset_ids:
            return set()

    query = folders_graphql_query({"id"})
    query.set_variable_value("projectName", project_name)
    query.set_variable_value("folderHasSubsets", True)
    if asset_ids:
        query.set_variable_value("folderIds", list(asset_ids))

    con = get_server_api_connection()
    parsed_data = query.query(con)
    folders = parsed_data["project"]["folders"]
    return {
        folder["id"]
        for folder in folders
    }


def get_subset_by_id(project_name, subset_id, fields=None):
    subsets = get_subsets(project_name, subset_ids=[subset_id], fields=fields)
    if subsets:
        return subsets[0]
    return None


def get_subset_by_name(project_name, subset_name, asset_id, fields=None):
    subsets = get_subsets(
        project_name,
        subset_names=[subset_name],
        asset_ids=[asset_id],
        fields=fields
    )
    if subsets:
        return subsets[0]
    return None


def get_subsets(
    project_name,
    subset_ids=None,
    subset_names=None,
    asset_ids=None,
    names_by_asset_ids=None,
    archived=False,
    fields=None
):
    return _get_subsets(
        project_name,
        subset_ids,
        subset_names,
        asset_ids,
        names_by_asset_ids,
        archived,
        fields
    )


def get_subset_families(project_name, subset_ids=None):
    if subset_ids is not None:
        subsets = get_subsets(
            project_name,
            subset_ids=subset_ids,
            fields=["data.family"]
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

    con = get_server_api_connection()
    parsed_data = query.query(con)

    return set(parsed_data.get("project", {}).get("subsetFamilies", []))


def get_version_by_id(project_name, version_id, fields=None):
    versions = get_versions(
        project_name,
        version_ids=[version_id],
        fields=fields,
        hero=True
    )
    if versions:
        return versions[0]
    return None


def get_version_by_name(project_name, version, subset_id, fields=None):
    versions = get_versions(
        project_name,
        subset_ids=[subset_id],
        versions=[version],
        fields=fields
    )
    if versions:
        return versions[0]
    return None


def get_versions(
    project_name,
    version_ids=None,
    subset_ids=None,
    versions=None,
    hero=False,
    fields=None
):
    return _get_versions(
        project_name,
        version_ids,
        subset_ids,
        versions,
        hero=hero,
        standard=True,
        fields=fields
    )


def get_hero_version_by_id(project_name, version_id, fields=None):
    versions = get_hero_versions(
        project_name,
        version_ids=[version_id],
        fields=fields
    )
    if versions:
        return versions[0]
    return None


def get_hero_version_by_subset_id(project_name, subset_id, fields=None):
    versions = get_hero_versions(
        project_name,
        subset_ids=[subset_id],
        fields=fields
    )
    if versions:
        return versions[0]
    return None


def get_hero_versions(
    project_name,
    subset_ids=None,
    version_ids=None,
    fields=None
):
    return _get_versions(
        project_name,
        version_ids=version_ids,
        subset_ids=subset_ids,
        hero=True,
        standard=False,
        fields=fields
    )


def get_last_versions(project_name, subset_ids, fields=None):
    versions = _get_versions(
        project_name,
        subset_ids=subset_ids,
        latest=True,
        fields=fields
    )
    return {
        version["parent"]: version
        for version in versions
    }


def get_last_version_by_subset_id(project_name, subset_id, fields=None):
    versions = _get_versions(
        project_name,
        subset_ids=[subset_id],
        latest=True,
        fields=fields
    )
    if not versions:
        return versions[0]
    return None


def get_last_version_by_subset_name(
    project_name, subset_name, asset_id=None, asset_name=None, fields=None
):
    if not asset_id and not asset_name:
        return None

    if not asset_id:
        asset = get_asset_by_name(project_name, asset_name, fields=["_id"])
        if not asset:
            return None
        asset_id = asset["_id"]

    subset = get_subset_by_name(
        project_name, subset_name, asset_id, fields=["_id"]
    )
    if not subset:
        return None
    return get_last_version_by_subset_id(
        project_name, subset["id"], fields=fields
    )


def get_output_link_versions(*args, **kwargs):
    raise NotImplementedError("'get_output_link_versions' not implemented")


def version_is_latest(project_name, version_id):
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

    con = get_server_api_connection()
    parsed_data = query.query(con)
    latest_version = (
        parsed_data["project"]["version"]["subset"]["latestVersion"]
    )
    return latest_version["id"] == version_id


def get_representation_by_id(project_name, representation_id, fields=None):
    representations = get_representations(
        project_name,
        representation_ids=[representation_id],
        fields=fields
    )
    if representations:
        return representations[0]
    return None


def get_representation_by_name(
    project_name, representation_name, version_id, fields=None
):
    representations = get_representations(
        project_name,
        representation_names=[representation_name],
        version_ids=[version_id],
        fields=fields
    )
    if representations:
        return representations[0]
    return None


def get_representations(
    project_name,
    representation_ids=None,
    representation_names=None,
    version_ids=None,
    context_filters=None,
    names_by_version_ids=None,
    archived=False,
    standard=True,
    fields=None
):
    if context_filters is not None:
        # TODO should we add the support?
        # - there was ability to fitler using regex
        raise ValueError("OP v4 can't filter by representation context.")

    if not archived and not standard:
        return []

    if archived and not standard:
        active = False
    elif not archived and standard:
        active = True
    else:
        active = None

    fields = _representation_fields_v3_to_v4(fields)
    representations = get_v4_representations(
        project_name,
        representation_ids,
        representation_names,
        version_ids,
        names_by_version_ids,
        active,
        fields
    )
    return [
        _convert_v4_representation_to_v3(repre)
        for repre in representations
    ]


def get_representation_parents(project_name, representation):
    if not representation:
        return None

    repre_id = representation["_id"]
    parents_by_repre_id = get_representations_parents(
        project_name, [representation]
    )
    return parents_by_repre_id[repre_id]


def get_representations_parents(project_name, representations):
    repre_ids = {
        repre["_id"]
        for repre in representations
    }
    parents = get_v4_representations_parents(project_name, repre_ids)
    folder_ids = set()
    for parents in parents.values():
        folder_ids.add(parents[2]["id"])

    tasks_by_folder_id = {}

    new_parents = {}
    for repre_id, parents in parents.items():
        version, subset, folder, project = parents
        folder_tasks = tasks_by_folder_id.get(folder["id"]) or {}
        folder["tasks"] = folder_tasks
        new_parents[repre_id] = (
            _convert_v4_version_to_v3(version),
            _convert_v4_subset_to_v3(subset),
            _convert_v4_folder_to_v3(folder, project_name),
            project
        )
    return new_parents


def get_v4_representations_parents(project_name, representation_ids):
    if not representation_ids:
        return {}

    project = get_project(project_name)
    repre_ids = set(representation_ids)
    output = {
        repre_id: (None, None, None, None)
        for repre_id in representation_ids
    }

    query = reprersentations_parents_qraphql_query()
    query.set_variable_value("projectName", project_name)
    query.set_variable_value("representationIds", list(repre_ids))

    con = get_server_api_connection()

    parsed_data = query.query(con)
    for repre in parsed_data["project"]["representations"]:
        repre_id = repre["id"]
        version = repre.pop("version")
        subset = version.pop("subset")
        folder = subset.pop("folder")
        output[repre_id] = (version, subset, folder, project)

    return output


def get_archived_representations(*args, **kwargs):
    raise NotImplementedError("'get_archived_representations' not implemented")


def get_thumbnail(project_name, thumbnail_id, fields=None):
    # TODO thumbnails are handled in a different way
    return None


def get_thumbnails(project_name, thumbnail_ids, fields=None):
    # TODO thumbnails are handled in a different way
    return []


def get_thumbnail_id_from_source(project_name, src_type, src_id):
    """Receive thumbnail id from source entity.

    Args:
        project_name (str): Name of project where to look for queried entities.
        src_type (str): Type of source entity ('asset', 'version').
        src_id (Union[str, ObjectId]): Id of source entity.

    Returns:
        ObjectId: Thumbnail id assigned to entity.
        None: If Source entity does not have any thumbnail id assigned.
    """

    if not src_type or not src_id:
        return None

    if src_type == "subset":
        subset = get_subset_by_id(
            project_name, src_id, fields=["data.thumbnail_id"]
        ) or {}
        return subset.get("data", {}).get("thumbnail_id")

    if src_type == "subset":
        subset = get_asset_by_id(
            project_name, src_id, fields=["data.thumbnail_id"]
        ) or {}
        return subset.get("data", {}).get("thumbnail_id")

    return None


def get_workfile_info(
    project_name, asset_id, task_name, filename, fields=None
):
    # TODO workfile info not implemented in v4 yet
    return None
