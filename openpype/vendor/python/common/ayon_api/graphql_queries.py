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


def add_links_fields(entity_field, nested_fields):
    if "links" not in nested_fields:
        return
    links_fields = nested_fields.pop("links")

    link_edge_fields = {
        "id",
        "linkType",
        "projectName",
        "entityType",
        "entityId",
        "direction",
        "description",
        "author",
    }
    if isinstance(links_fields, dict):
        simple_fields = set(links_fields)
        simple_variant = len(simple_fields - link_edge_fields) == 0
    else:
        simple_variant = True
        simple_fields = link_edge_fields

    link_field = entity_field.add_field_with_edges("links")

    link_type_var = link_field.add_variable("linkTypes", "[String!]")
    link_dir_var = link_field.add_variable("linkDirection", "String!")
    link_field.set_filter("linkTypes", link_type_var)
    link_field.set_filter("direction", link_dir_var)

    if simple_variant:
        for key in simple_fields:
            link_field.add_edge_field(key)
        return

    query_queue = collections.deque()
    for key, value in links_fields.items():
        if key in link_edge_fields:
            link_field.add_edge_field(key)
            continue
        query_queue.append((key, value, link_field))

    while query_queue:
        item = query_queue.popleft()
        key, value, parent = item
        field = parent.add_field(key)
        if value is FIELD_VALUE:
            continue

        for k, v in value.items():
            query_queue.append((k, v, field))


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
    projects_field = query.add_field_with_edges("projects")

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

    folders_field = project_field.add_field_with_edges("folders")
    folders_field.set_filter("ids", folder_ids_var)
    folders_field.set_filter("parentIds", parent_folder_ids_var)
    folders_field.set_filter("names", folder_names_var)
    folders_field.set_filter("paths", folder_paths_var)
    folders_field.set_filter("hasSubsets", has_subsets_var)

    nested_fields = fields_to_dict(fields)
    add_links_fields(folders_field, nested_fields)

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

    tasks_field = project_field.add_field_with_edges("tasks")
    tasks_field.set_filter("ids", task_ids_var)
    # WARNING: At moment when this been created 'names' filter is not supported
    tasks_field.set_filter("names", task_names_var)
    tasks_field.set_filter("taskTypes", task_types_var)
    tasks_field.set_filter("folderIds", folder_ids_var)

    nested_fields = fields_to_dict(fields)
    add_links_fields(tasks_field, nested_fields)

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

    subsets_field = project_field.add_field_with_edges("subsets")
    subsets_field.set_filter("ids", subset_ids_var)
    subsets_field.set_filter("names", subset_names_var)
    subsets_field.set_filter("folderIds", folder_ids_var)

    nested_fields = fields_to_dict(set(fields))
    add_links_fields(subsets_field, nested_fields)

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
    versions_var = query.add_variable("versions", "[Int!]")
    hero_only_var = query.add_variable("heroOnly", "Boolean")
    latest_only_var = query.add_variable("latestOnly", "Boolean")
    hero_or_latest_only_var = query.add_variable(
        "heroOrLatestOnly", "Boolean"
    )

    project_field = query.add_field("project")
    project_field.set_filter("name", project_name_var)

    subsets_field = project_field.add_field_with_edges("versions")
    subsets_field.set_filter("ids", version_ids_var)
    subsets_field.set_filter("subsetIds", subset_ids_var)
    subsets_field.set_filter("versions", versions_var)
    subsets_field.set_filter("heroOnly", hero_only_var)
    subsets_field.set_filter("latestOnly", latest_only_var)
    subsets_field.set_filter("heroOrLatestOnly", hero_or_latest_only_var)

    nested_fields = fields_to_dict(set(fields))
    add_links_fields(subsets_field, nested_fields)

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

    repres_field = project_field.add_field_with_edges("representations")
    repres_field.set_filter("ids", repre_ids_var)
    repres_field.set_filter("versionIds", version_ids_var)
    repres_field.set_filter("names", repre_names_var)

    nested_fields = fields_to_dict(set(fields))
    add_links_fields(repres_field, nested_fields)

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


def representations_parents_qraphql_query(
    version_fields, subset_fields, folder_fields
):
    query = GraphQlQuery("RepresentationsParentsQuery")

    project_name_var = query.add_variable("projectName", "String!")
    repre_ids_var = query.add_variable("representationIds", "[String!]")

    project_field = query.add_field("project")
    project_field.set_filter("name", project_name_var)

    repres_field = project_field.add_field_with_edges("representations")
    repres_field.add_field("id")
    repres_field.set_filter("ids", repre_ids_var)
    version_field = repres_field.add_field("version")

    fields_queue = collections.deque()
    for key, value in fields_to_dict(version_fields).items():
        fields_queue.append((key, value, version_field))

    subset_field = version_field.add_field("subset")
    for key, value in fields_to_dict(subset_fields).items():
        fields_queue.append((key, value, subset_field))

    folder_field = subset_field.add_field("folder")
    for key, value in fields_to_dict(folder_fields).items():
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


def workfiles_info_graphql_query(fields):
    query = GraphQlQuery("WorkfilesInfo")
    project_name_var = query.add_variable("projectName", "String!")
    workfiles_info_ids = query.add_variable("workfileIds", "[String!]")
    task_ids_var = query.add_variable("taskIds", "[String!]")
    paths_var = query.add_variable("paths", "[String!]")

    project_field = query.add_field("project")
    project_field.set_filter("name", project_name_var)

    workfiles_field = project_field.add_field_with_edges("workfiles")
    workfiles_field.set_filter("ids", workfiles_info_ids)
    workfiles_field.set_filter("taskIds", task_ids_var)
    workfiles_field.set_filter("paths", paths_var)

    nested_fields = fields_to_dict(set(fields))
    add_links_fields(workfiles_field, nested_fields)

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, workfiles_field))

    while query_queue:
        item = query_queue.popleft()
        key, value, parent = item
        field = parent.add_field(key)
        if value is FIELD_VALUE:
            continue

        for k, v in value.items():
            query_queue.append((k, v, field))
    return query


def events_graphql_query(fields):
    query = GraphQlQuery("Events")
    topics_var = query.add_variable("eventTopics", "[String!]")
    projects_var = query.add_variable("projectNames", "[String!]")
    states_var = query.add_variable("eventStates", "[String!]")
    users_var = query.add_variable("eventUsers", "[String!]")
    include_logs_var = query.add_variable("includeLogsFilter", "Boolean!")

    events_field = query.add_field_with_edges("events")
    events_field.set_filter("topics", topics_var)
    events_field.set_filter("projects", projects_var)
    events_field.set_filter("states", states_var)
    events_field.set_filter("users", users_var)
    events_field.set_filter("includeLogs", include_logs_var)

    nested_fields = fields_to_dict(set(fields))

    query_queue = collections.deque()
    for key, value in nested_fields.items():
        query_queue.append((key, value, events_field))

    while query_queue:
        item = query_queue.popleft()
        key, value, parent = item
        field = parent.add_field(key)
        if value is FIELD_VALUE:
            continue

        for k, v in value.items():
            query_queue.append((k, v, field))
    return query
