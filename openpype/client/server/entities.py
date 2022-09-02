from .graphql import fields_to_graphql
from .server import get_server_api_connection


project_direct_fields_mapping_v3_to_v4 = {
    "_id": {"name"},
    "name": {"name"},
    "data": {"data", "attrib", "code"},
    "data.library_project": {"library"},
    "data.code": {"code"},
    "data.active": {"active"},
}


def project_fields_v3_to_v4(fields):
    # TODO config fields
    # - config.apps
    # - config.groups
    if not fields:
        return None

    output = set()
    for field in fields:
        if field.startswith("config"):
            return None

        if field in project_direct_fields_mapping_v3_to_v4:
            output |= project_direct_fields_mapping_v3_to_v4[field]

        elif field.startswith("data"):
            new_field = "attrib" + field[:4]
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
        # Fake id
        "_id": project_name,
        "name": project_name
    }
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


def _get_projects(active=None, library=None, fields=None):
    con = get_server_api_connection()
    fields = project_fields_v3_to_v4(fields)
    if not fields:
        return con.get_rest_projects(active, library)

    graphql = "\n".join([
        "query ProjectsQuery { projects { edges { node",
        fields_to_graphql(fields),
        "}}}"
    ])
    response = con.query(graphql)
    output = []
    for edge in response.data["data"]["projects"]["edges"]:
        output.append(edge.pop("node"))
    return output


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

    con = get_server_api_connection()
    if active and inactive:
        active = None

    fields = project_fields_v3_to_v4(fields)
    if not fields:
        return _convert_v4_project_to_v3(
            con.get_rest_project(active)
        )

    fields.discard("name")
    graphql = "\n".join([
        "query ProjectQuery($projectName: String!) {"
        "project(name: $projectName)",
        fields_to_graphql(fields),
        "}"
    ])
    response = con.query(graphql, projectName=project_name)
    data = response.data["data"]["project"]
    data["name"] = project_name
    return _convert_v4_project_to_v3(data)


def get_whole_project(*args, **kwargs):
    raise NotImplementedError("'get_whole_project' not implemented")


def get_asset_by_id(*args, **kwargs):
    raise NotImplementedError("'get_asset_by_id' not implemented")


def get_asset_by_name(*args, **kwargs):
    raise NotImplementedError("'get_asset_by_name' not implemented")


def get_assets(*args, **kwargs):
    raise NotImplementedError("'get_assets' not implemented")


def get_archived_assets(*args, **kwargs):
    raise NotImplementedError("'get_archived_assets' not implemented")


def get_asset_ids_with_subsets(*args, **kwargs):
    raise NotImplementedError("'get_asset_ids_with_subsets' not implemented")


def get_subset_by_id(*args, **kwargs):
    raise NotImplementedError("'get_subset_by_id' not implemented")


def get_subset_by_name(*args, **kwargs):
    raise NotImplementedError("'get_subset_by_name' not implemented")


def get_subsets(*args, **kwargs):
    raise NotImplementedError("'get_subsets' not implemented")


def get_subset_families(*args, **kwargs):
    raise NotImplementedError("'get_subset_families' not implemented")


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
