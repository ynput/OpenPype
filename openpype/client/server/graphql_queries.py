import collections

from .constants import (
    DEFAULT_FOLDER_FIELDS,
    DEFAULT_SUBSET_FIELDS,
    DEFAULT_VERSION_FIELDS,
)
from .graphql import FIELD_VALUE, GraphQlQuery


def fields_to_dict(fields):
    if not fields:
        return None

    output = {}
    for field in fields:
        hierarchy = field.split(".")
        last = hierarchy.pop(-1)
        value = output
        for part in hierarchy:
            if value is FIELD_VALUE:
                break

            if part not in value:
                value[part] = {}
            value = value[part]

        if value is not FIELD_VALUE:
            value[last] = FIELD_VALUE
    return output


def project_graphql_query(fields):
    query = GraphQlQuery("ProjectQuery")
    project_name_var = query.add_variable("projectName", "String!")
    project_field = query.add_field("project")
    project_field.set_filter("name", project_name_var)

    nested_fields = fields_to_dict(fields)

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, project_field))

    while query_queue:
        item = query_queue.popleft()
        key, value, parent = item
        field = parent.add_field(key)
        if value is FIELD_VALUE:
            continue

        for k, v in value.items():
            query_queue.append((k, v, field))
    return query


def projects_graphql_query(fields):
    query = GraphQlQuery("ProjectsQuery")
    projects_field = query.add_field("projects", has_edges=True)

    nested_fields = fields_to_dict(fields)

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, projects_field))

    while query_queue:
        item = query_queue.popleft()
        key, value, parent = item
        field = parent.add_field(key)
        if value is FIELD_VALUE:
            continue

        for k, v in value.items():
            query_queue.append((k, v, field))
    return query


def folders_graphql_query(fields):
    query = GraphQlQuery("FoldersQuery")
    project_name_var = query.add_variable("projectName", "String!")
    folder_ids_var = query.add_variable("folderIds", "[String!]")
    parent_folder_ids_var = query.add_variable("parentFolderIds", "[String!]")
    folder_paths_var = query.add_variable("folderPaths", "[String!]")
    folder_names_var = query.add_variable("folderNames", "[String!]")
    has_subsets_var = query.add_variable("folderHasSubsets", "Boolean!")

    project_field = query.add_field("project")
    project_field.set_filter("name", project_name_var)

    folders_field = project_field.add_field("folders", has_edges=True)
    folders_field.set_filter("ids", folder_ids_var)
    folders_field.set_filter("parentIds", parent_folder_ids_var)
    folders_field.set_filter("names", folder_names_var)
    folders_field.set_filter("paths", folder_paths_var)
    folders_field.set_filter("hasSubsets", has_subsets_var)

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


def folders_tasks_graphql_query(fields):
    query = GraphQlQuery("FoldersQuery")
    project_name_var = query.add_variable("projectName", "String!")
    folder_ids_var = query.add_variable("folderIds", "[String!]")
    parent_folder_ids_var = query.add_variable("parentFolderIds", "[String!]")
    folder_paths_var = query.add_variable("folderPaths", "[String!]")
    folder_names_var = query.add_variable("folderNames", "[String!]")
    has_subsets_var = query.add_variable("folderHasSubsets", "Boolean!")

    project_field = query.add_field("project")
    project_field.set_filter("name", project_name_var)

    folders_field = project_field.add_field("folders", has_edges=True)
    folders_field.set_filter("ids", folder_ids_var)
    folders_field.set_filter("parentIds", parent_folder_ids_var)
    folders_field.set_filter("names", folder_names_var)
    folders_field.set_filter("paths", folder_paths_var)
    folders_field.set_filter("hasSubsets", has_subsets_var)

    fields = set(fields)
    fields.discard("tasks")
    tasks_field = folders_field.add_field("tasks", has_edges=True)
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


def tasks_graphql_query(fields):
    query = GraphQlQuery("TasksQuery")
    project_name_var = query.add_variable("projectName", "String!")
    task_ids_var = query.add_variable("taskIds", "[String!]")
    task_names_var = query.add_variable("taskNames", "[String!]")
    task_types_var = query.add_variable("taskTypes", "[String!]")
    folder_ids_var = query.add_variable("folderIds", "[String!]")

    project_field = query.add_field("project")
    project_field.set_filter("name", project_name_var)

    tasks_field = project_field.add_field("folders", has_edges=True)
    tasks_field.set_filter("ids", task_ids_var)
    # WARNING: At moment when this been created 'names' filter is not supported
    tasks_field.set_filter("names", task_names_var)
    tasks_field.set_filter("taskTypes", task_types_var)
    tasks_field.set_filter("folderIds", folder_ids_var)

    nested_fields = fields_to_dict(fields)

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, tasks_field))

    while query_queue:
        item = query_queue.popleft()
        key, value, parent = item
        field = parent.add_field(key)
        if value is FIELD_VALUE:
            continue

        for k, v in value.items():
            query_queue.append((k, v, field))
    return query


def subsets_graphql_query(fields):
    query = GraphQlQuery("SubsetsQuery")

    project_name_var = query.add_variable("projectName", "String!")
    folder_ids_var = query.add_variable("folderIds", "[String!]")
    subset_ids_var = query.add_variable("subsetIds", "[String!]")
    subset_names_var = query.add_variable("subsetNames", "[String!]")

    project_field = query.add_field("project")
    project_field.set_filter("name", project_name_var)

    subsets_field = project_field.add_field("subsets", has_edges=True)
    subsets_field.set_filter("ids", subset_ids_var)
    subsets_field.set_filter("names", subset_names_var)
    subsets_field.set_filter("folderIds", folder_ids_var)

    nested_fields = fields_to_dict(set(fields))

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, subsets_field))

    while query_queue:
        item = query_queue.popleft()
        key, value, parent = item
        field = parent.add_field(key)
        if value is FIELD_VALUE:
            continue

        for k, v in value.items():
            query_queue.append((k, v, field))
    return query


def versions_graphql_query(fields):
    query = GraphQlQuery("VersionsQuery")

    project_name_var = query.add_variable("projectName", "String!")
    subset_ids_var = query.add_variable("subsetIds", "[String!]")
    version_ids_var = query.add_variable("versionIds", "[String!]")
    versions_var = query.add_variable("versions", "[Int]")
    hero_only_var = query.add_variable("heroOnly", "Boolean")
    latest_only_var = query.add_variable("latestOnly", "Boolean")
    hero_or_latest_only_var = query.add_variable(
        "heroOrLatestOnly", "Boolean"
    )

    project_field = query.add_field("project")
    project_field.set_filter("name", project_name_var)

    subsets_field = project_field.add_field("versions", has_edges=True)
    subsets_field.set_filter("ids", version_ids_var)
    subsets_field.set_filter("subsetIds", subset_ids_var)
    subsets_field.set_filter("versions", versions_var)
    subsets_field.set_filter("heroOnly", hero_only_var)
    subsets_field.set_filter("latestOnly", latest_only_var)
    subsets_field.set_filter("heroOrLatestOnly", hero_or_latest_only_var)

    nested_fields = fields_to_dict(set(fields))

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, subsets_field))

    while query_queue:
        item = query_queue.popleft()
        key, value, parent = item
        field = parent.add_field(key)
        if value is FIELD_VALUE:
            continue

        for k, v in value.items():
            query_queue.append((k, v, field))
    return query


def representations_graphql_query(fields):
    query = GraphQlQuery("RepresentationsQuery")

    project_name_var = query.add_variable("projectName", "String!")
    repre_ids_var = query.add_variable("representationIds", "[String!]")
    repre_names_var = query.add_variable("representationNames", "[String!]")
    version_ids_var = query.add_variable("versionIds", "[String!]")

    project_field = query.add_field("project")
    project_field.set_filter("name", project_name_var)

    repres_field = project_field.add_field("representations", has_edges=True)
    repres_field.set_filter("ids", repre_ids_var)
    repres_field.set_filter("versionIds", version_ids_var)
    repres_field.set_filter("representationNames", repre_names_var)

    nested_fields = fields_to_dict(set(fields))

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, repres_field))

    while query_queue:
        item = query_queue.popleft()
        key, value, parent = item
        field = parent.add_field(key)
        if value is FIELD_VALUE:
            continue

        for k, v in value.items():
            query_queue.append((k, v, field))
    return query


def reprersentations_parents_qraphql_query():
    query = GraphQlQuery("RepresentationsParentsQuery")

    project_name_var = query.add_variable("projectName", "String!")
    repre_ids_var = query.add_variable("representationIds", "[String!]")

    project_field = query.add_field("project")
    project_field.set_filter("name", project_name_var)

    repres_field = project_field.add_field("representations", has_edges=True)
    repres_field.add_field("id")
    repres_field.set_filter("ids", repre_ids_var)
    version_field = repres_field.add_field("version")

    fields_queue = collections.deque()
    for key, value in fields_to_dict(DEFAULT_VERSION_FIELDS).items():
        fields_queue.append((key, value, version_field))

    subset_field = version_field.add_field("subset")
    for key, value in fields_to_dict(DEFAULT_SUBSET_FIELDS).items():
        fields_queue.append((key, value, subset_field))

    folder_field = subset_field.add_field("folder")
    for key, value in fields_to_dict(DEFAULT_FOLDER_FIELDS).items():
        fields_queue.append((key, value, folder_field))

    while fields_queue:
        item = fields_queue.popleft()
        key, value, parent = item
        field = parent.add_field(key)
        if value is FIELD_VALUE:
            continue

        for k, v in value.items():
            fields_queue.append((k, v, field))

    return query
