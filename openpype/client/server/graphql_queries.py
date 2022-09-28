import collections

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
    project_query = query.add_field("project")
    project_query.set_filter("name", project_name_var)

    nested_fields = fields_to_dict(fields)

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, project_query))

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
    projects_query = query.add_field("projects", has_edges=True)

    nested_fields = fields_to_dict(fields)

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, projects_query))

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

    project_query = query.add_field("project")
    project_query.set_filter("name", project_name_var)

    folders_query = project_query.add_field("folders", has_edges=True)
    folders_query.set_filter("ids", folder_ids_var)
    folders_query.set_filter("parentIds", parent_folder_ids_var)
    folders_query.set_filter("names", folder_names_var)
    folders_query.set_filter("paths", folder_paths_var)
    folders_query.set_filter("hasSubsets", has_subsets_var)

    fields = set(fields)
    if "tasks" in fields:
        fields.remove("tasks")
        tasks_query = folders_query.add_field("tasks", has_edges=True)
        tasks_query.add_field("name")
        tasks_query.add_field("taskType")

    nested_fields = fields_to_dict(fields)

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, folders_query))

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

    project_query = query.add_field("project")
    project_query.set_filter("name", project_name_var)

    subsets_query = project_query.add_field("subsets", has_edges=True)
    subsets_query.set_filter("ids", subset_ids_var)
    subsets_query.set_filter("names", subset_names_var)
    subsets_query.set_filter("folderIds", folder_ids_var)

    nested_fields = fields_to_dict(set(fields))

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, subsets_query))

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

    project_query = query.add_field("project")
    project_query.set_filter("name", project_name_var)

    subsets_query = project_query.add_field("versions", has_edges=True)
    subsets_query.set_filter("ids", version_ids_var)
    subsets_query.set_filter("subsetIds", subset_ids_var)
    subsets_query.set_filter("versions", versions_var)
    subsets_query.set_filter("heroOnly", hero_only_var)
    subsets_query.set_filter("latestOnly", latest_only_var)
    subsets_query.set_filter("heroOrLatestOnly", hero_or_latest_only_var)

    nested_fields = fields_to_dict(set(fields))

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, subsets_query))

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

    project_query = query.add_field("project")
    project_query.set_filter("name", project_name_var)

    repres_query = project_query.add_field("representations", has_edges=True)
    repres_query.set_filter("ids", repre_ids_var)
    repres_query.set_filter("versionIds", version_ids_var)
    repres_query.set_filter("representationNames", repre_names_var)

    nested_fields = fields_to_dict(set(fields))

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, repres_query))

    while query_queue:
        item = query_queue.popleft()
        key, value, parent = item
        field = parent.add_field(key)
        if value is FIELD_VALUE:
            continue

        for k, v in value.items():
            query_queue.append((k, v, field))
    return query
