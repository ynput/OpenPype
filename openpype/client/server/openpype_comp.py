import collections
import json

import six
from ayon_api.graphql import GraphQlQuery, FIELD_VALUE, fields_to_dict

from .constants import DEFAULT_FOLDER_FIELDS


def folders_tasks_graphql_query(fields):
    query = GraphQlQuery("FoldersQuery")
    project_name_var = query.add_variable("projectName", "String!")
    folder_ids_var = query.add_variable("folderIds", "[String!]")
    parent_folder_ids_var = query.add_variable("parentFolderIds", "[String!]")
    folder_paths_var = query.add_variable("folderPaths", "[String!]")
    folder_names_var = query.add_variable("folderNames", "[String!]")
    has_products_var = query.add_variable("folderHasProducts", "Boolean!")

    project_field = query.add_field("project")
    project_field.set_filter("name", project_name_var)

    folders_field = project_field.add_field_with_edges("folders")
    folders_field.set_filter("ids", folder_ids_var)
    folders_field.set_filter("parentIds", parent_folder_ids_var)
    folders_field.set_filter("names", folder_names_var)
    folders_field.set_filter("paths", folder_paths_var)
    folders_field.set_filter("hasProducts", has_products_var)

    fields = set(fields)
    fields.discard("tasks")
    tasks_field = folders_field.add_field_with_edges("tasks")
    tasks_field.add_field("name")
    tasks_field.add_field("taskType")

    nested_fields = fields_to_dict(fields)

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, folders_field))

    while query_queue:
        item = query_queue.popleft()
        key, value, parent = item
        field = parent.add_field(key)
        if value is FIELD_VALUE:
            continue

        for k, v in value.items():
            query_queue.append((k, v, field))
    return query


def get_folders_with_tasks(
    con,
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
    an inefficient way how folders and tasks are queried so it was added only
    as compatibility function.

    Todos:
        Folder name won't be unique identifier, so we should add folder path
            filtering.

    Notes:
        Filter 'active' don't have direct filter in GraphQl.

    Args:
        con (ServerAPI): Connection to server.
        project_name (str): Name of project where folders are.
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

    Yields:
        Dict[str, Any]: Queried folder entities.
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

    if fields:
        fields = set(fields)
    else:
        fields = con.get_default_fields_for_type("folder")
        fields |= DEFAULT_FOLDER_FIELDS

    if active is not None:
        fields.add("active")

    query = folders_tasks_graphql_query(fields)
    for attr, filter_value in filters.items():
        query.set_variable_value(attr, filter_value)

    parsed_data = query.query(con)
    folders = parsed_data["project"]["folders"]
    for folder in folders:
        if active is not None and folder["active"] is not active:
            continue
        folder_data = folder.get("data")
        if isinstance(folder_data, six.string_types):
            folder["data"] = json.loads(folder_data)
        yield folder
