import collections

from .graphql import (
    GraphQlQuery,
    project_graphql_query,
    projects_graphql_query,
    folders_graphql_query,
    subsets_graphql_query,
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
FOLDER_ATTRIBS = {
    "clipIn",
    "clipOut",
    "fps",
    "frameEnd",
    "handleEnd",
    "frameStart",
    "handleStart",
    "pixelAspect",
    "resolutionHeight",
    "resolutionWidth",
}
FOLDER_ATTRIBS_FIELDS = {
    "attrib.{}".format(attr)
    for attr in FOLDER_ATTRIBS
}
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
    "data.thumbnail_id": {"thumbnailId"},
    "parent": {"projectName"}
}

# NOTE: There are for v3 compatibility
DEFAULT_FOLDER_FIELDS = {
    "id",
    "name",
    "parentId",
    "tasks",
    "active",
    "parents",
} | FOLDER_ATTRIBS_FIELDS

# --- Subset entity ---
SUBSET_ATTRIBS = {
    "subsetGroup",
}
SUBSET_ATTRIBS_FIELDS = {
    "attrib.{}".format(attr)
    for attr in SUBSET_ATTRIBS
}
DEFAULT_SUBSET_FIELDS = {
    "id",
    "name",
    "active",
    "family",
    "folderId",
} | SUBSET_ATTRIBS_FIELDS

SUBSET_FIELDS_MAPPING_V3_V4 = {
    "_id": {"id"},
    "name": {"name"},
    "data.active": {"active"},
    "parent": {"folderId"}
}


# CURRENT_PROJECT_CONFIG_SCHEMA = "openpype:config-2.0"
# CURRENT_REPRESENTATION_SCHEMA = "openpype:representation-2.0"
# CURRENT_WORKFILE_INFO_SCHEMA = "openpype:workfile-1.0"
# CURRENT_THUMBNAIL_SCHEMA = "openpype:thumbnail-1.0"


def _project_fields_v3_to_v4(fields):
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
    if not fields:
        return set(DEFAULT_FOLDER_FIELDS)

    output = set()
    for field in fields:
        if field in ("schema", "type"):
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
    output = {}
    for task in tasks:
        task_name = task["name"]
        new_task = {
            "type": task["taskType"]
        }
        output[task_name] = new_task
    return output


def _convert_v4_folder_to_v3(folder):
    output = {
        "_id": folder["id"],
        "type": "asset",
        "schema": "openpype:asset-3.0"
    }

    output_data = folder.get("data") or {}

    if "name" in folder:
        output["name"] = folder["name"]
        output_data["label"] = folder["name"]

    for data_key, key in (
        ("visualParent", "parentId"),
        ("active", "active")
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
    if not fields:
        return set(DEFAULT_SUBSET_FIELDS)

    output = set()
    for field in fields:
        if field in ("schema", "type"):
            continue

        if field in SUBSET_FIELDS_MAPPING_V3_V4:
            output |= SUBSET_FIELDS_MAPPING_V3_V4[field]

        elif field == "data":
            output.add("family")
            output.add("attrib.subsetGroup")

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


def _get_projects(active=None, library=None, fields=None):
    con = get_server_api_connection()
    fields = _project_fields_v3_to_v4(fields)
    if not fields:
        return con.get_rest_projects(active, library)

    query = projects_graphql_query(fields)
    query_str = query.calculate_query()
    response = con.query(query_str)
    parsed_data = query.parse_result(response.data["data"])

    output = []
    for project in parsed_data["projects"]:
        output.append(project)
    return output


def _get_folders(
    project_name,
    folder_ids,
    folder_names,
    parent_ids,
    archived,
    fields
):
    if not project_name:
        return []

    fields = _folder_fields_v3_to_v4(fields)
    filters = {
        "projectName": project_name
    }
    if folder_ids is not None:
        folder_ids = set(folder_ids)
        if not folder_ids:
            return []
        filters["folderIds"] = list(folder_ids)

    if folder_names is not None:
        folder_names = set(folder_names)
        if not folder_names:
            return []
        filters["folderNames"] = list(folder_names)

    if parent_ids is not None:
        parent_ids = set(parent_ids)
        if not parent_ids:
            return []
        filters["parentFolderIds"] = list(parent_ids)

    con = get_server_api_connection()

    query = folders_graphql_query(fields)
    for attr, filter_value in filters.items():
        query.set_variable_value(attr, filter_value)

    query_str = query.calculate_query()
    variables = query.get_variables_values()

    response = con.query(query_str, **variables)

    parsed_data = query.parse_result(response.data["data"])
    output = []

    folders = parsed_data.get("project", {}).get("folders", [])
    expect_parent_id = "parentId" in fields
    for folder in folders:
        if expect_parent_id and "parentId" not in folder:
            folder["parentId"] = None
        output.append(_convert_v4_folder_to_v3(folder))
    return output


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
    for key in (
        "id",
        "active"
    ):
        fields.add(key)

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

    query_str = query.calculate_query()
    variables = query.get_variables_values()

    con = get_server_api_connection()
    response = con.query(query_str, **variables)

    parsed_data = query.parse_result(response.data["data"])

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


def get_projects(active=True, inactive=False, library=None, fields=None):
    if not active and not inactive:
        return []

    if active and inactive:
        active = None
    project_data = _get_projects(active, library, fields)
    return [
        _convert_v4_project_to_v3(project)
        for project in project_data
    ]


def get_project(project_name, active=True, inactive=False, fields=None):
    # Skip if both are disabled
    if not active and not inactive:
        return None

    if active and inactive:
        active = None

    con = get_server_api_connection()

    fields = _project_fields_v3_to_v4(fields)
    if not fields:
        return _convert_v4_project_to_v3(
            con.get_rest_project(project_name)
        )

    query = project_graphql_query(fields)
    query.set_variable_value("projectName", project_name)

    query_str = query.calculate_query()
    variables = query.get_variables_values()
    response = con.query(query_str, **variables)
    parsed_data = query.parse_result(response.data["data"])
    data = parsed_data["project"]
    data["name"] = project_name
    return _convert_v4_project_to_v3(data)


def get_whole_project(*args, **kwargs):
    raise NotImplementedError("'get_whole_project' not implemented")


def get_asset_by_id(project_name, asset_id, fields=None):
    assets = get_assets(project_name, asset_ids=[asset_id], fields=fields)
    if assets:
        return assets[0]
    return None


def get_asset_by_name(project_name, asset_name, fields=None):
    assets = get_assets(project_name, asset_names=[asset_name], fields=fields)
    if assets:
        return assets[0]
    return None


def get_assets(
    project_name,
    asset_ids=None,
    asset_names=None,
    parent_ids=None,
    archived=False,
    fields=None
):
    return _get_folders(
        project_name,
        asset_ids,
        asset_names,
        parent_ids,
        archived,
        fields
    )


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
    query_str = query.calculate_query()
    variables = query.get_variables_values()
    response = con.query(query_str, **variables)
    parsed_data = query.parse_result(response.data["data"])
    folders = parsed_data.get("project", {}).get("folders", [])
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
    project_query.filter("name", project_name_var)
    project_query.add_field("subsetFamilies")
    query_str = query.calculate_query()
    variables = query.get_variables_values()

    con = get_server_api_connection()
    response = con.query(query_str, **variables)

    parsed_data = query.parse_result(response.data["data"])
    return set(parsed_data.get("project", {}).get("subsetFamilies", []))


def get_version_by_id(*args, **kwargs):
    raise NotImplementedError("'get_version_by_id' not implemented")


def get_version_by_name(*args, **kwargs):
    raise NotImplementedError("'get_version_by_name' not implemented")


def get_versions(*args, **kwargs):
    raise NotImplementedError("'get_versions' not implemented")


def get_hero_version_by_id(*args, **kwargs):
    raise NotImplementedError("'get_hero_version_by_id' not implemented")


def get_hero_version_by_subset_id(*args, **kwargs):
    raise NotImplementedError("'get_hero_version_by_subset_id' not implemented")


def get_hero_versions(*args, **kwargs):
    raise NotImplementedError("'get_hero_versions' not implemented")


def get_last_versions(*args, **kwargs):
    raise NotImplementedError("'get_last_versions' not implemented")


def get_last_version_by_subset_id(*args, **kwargs):
    raise NotImplementedError("'get_last_version_by_subset_id' not implemented")


def get_last_version_by_subset_name(*args, **kwargs):
    raise NotImplementedError(
        "'get_last_version_by_subset_name' not implemented"
    )


def get_output_link_versions(*args, **kwargs):
    raise NotImplementedError("'get_output_link_versions' not implemented")


def version_is_latest(*args, **kwargs):
    raise NotImplementedError("'version_is_latest' not implemented")


def get_representation_by_id(*args, **kwargs):
    raise NotImplementedError("'get_representation_by_id' not implemented")


def get_representation_by_name(*args, **kwargs):
    raise NotImplementedError("'get_representation_by_name' not implemented")


def get_representations(*args, **kwargs):
    raise NotImplementedError("'get_representations' not implemented")


def get_representation_parents(*args, **kwargs):
    raise NotImplementedError("'get_representation_parents' not implemented")


def get_representations_parents(*args, **kwargs):
    raise NotImplementedError("'get_representations_parents' not implemented")


def get_archived_representations(*args, **kwargs):
    raise NotImplementedError("'get_archived_representations' not implemented")


def get_thumbnail(*args, **kwargs):
    raise NotImplementedError("'get_thumbnail' not implemented")


def get_thumbnails(*args, **kwargs):
    raise NotImplementedError("'get_thumbnails' not implemented")


def get_thumbnail_id_from_source(*args, **kwargs):
    raise NotImplementedError("'get_thumbnail_id_from_source' not implemented")


def get_workfile_info(*args, **kwargs):
    raise NotImplementedError("'get_workfile_info' not implemented")
