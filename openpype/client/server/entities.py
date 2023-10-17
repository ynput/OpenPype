import collections

from ayon_api import get_server_api_connection

from openpype.client.mongo.operations import CURRENT_THUMBNAIL_SCHEMA

from .openpype_comp import get_folders_with_tasks
from .conversion_utils import (
    project_fields_v3_to_v4,
    convert_v4_project_to_v3,

    folder_fields_v3_to_v4,
    convert_v4_folder_to_v3,

    subset_fields_v3_to_v4,
    convert_v4_subset_to_v3,

    version_fields_v3_to_v4,
    convert_v4_version_to_v3,

    representation_fields_v3_to_v4,
    convert_v4_representation_to_v3,

    workfile_info_fields_v3_to_v4,
    convert_v4_workfile_info_to_v3,
)


def get_projects(active=True, inactive=False, library=None, fields=None):
    if not active and not inactive:
        return

    if active and inactive:
        active = None
    elif active:
        active = True
    elif inactive:
        active = False

    con = get_server_api_connection()
    fields = project_fields_v3_to_v4(fields, con)
    for project in con.get_projects(active, library, fields=fields):
        yield convert_v4_project_to_v3(project)


def get_project(project_name, active=True, inactive=False, fields=None):
    # Skip if both are disabled
    con = get_server_api_connection()
    fields = project_fields_v3_to_v4(fields, con)
    return convert_v4_project_to_v3(
        con.get_project(project_name, fields=fields)
    )


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
    # Convert fields and add minimum required fields
    con = get_server_api_connection()
    fields = subset_fields_v3_to_v4(fields, con)
    if fields is not None:
        for key in (
            "id",
            "active"
        ):
            fields.add(key)

    active = True
    if archived:
        active = None

    for subset in con.get_products(
        project_name,
        subset_ids,
        subset_names,
        folder_ids=folder_ids,
        names_by_folder_ids=names_by_folder_ids,
        active=active,
        fields=fields,
    ):
        yield convert_v4_subset_to_v3(subset)


def _get_versions(
    project_name,
    version_ids=None,
    subset_ids=None,
    versions=None,
    hero=True,
    standard=True,
    latest=None,
    active=None,
    fields=None
):
    con = get_server_api_connection()

    fields = version_fields_v3_to_v4(fields, con)

    # Make sure 'productId' and 'version' are available when hero versions
    #   are queried
    if fields and hero:
        fields = set(fields)
        fields |= {"productId", "version"}

    queried_versions = con.get_versions(
        project_name,
        version_ids,
        subset_ids,
        versions,
        hero,
        standard,
        latest,
        active=active,
        fields=fields
    )

    versions = []
    hero_versions = []
    for version in queried_versions:
        if version["version"] < 0:
            hero_versions.append(version)
        else:
            versions.append(convert_v4_version_to_v3(version))

    if hero_versions:
        subset_ids = set()
        versions_nums = set()
        for hero_version in hero_versions:
            versions_nums.add(abs(hero_version["version"]))
            subset_ids.add(hero_version["productId"])

        hero_eq_versions = con.get_versions(
            project_name,
            product_ids=subset_ids,
            versions=versions_nums,
            hero=False,
            fields=["id", "version", "productId"]
        )
        hero_eq_by_subset_id = collections.defaultdict(list)
        for version in hero_eq_versions:
            hero_eq_by_subset_id[version["productId"]].append(version)

        for hero_version in hero_versions:
            abs_version = abs(hero_version["version"])
            subset_id = hero_version["productId"]
            version_id = None
            for version in hero_eq_by_subset_id.get(subset_id, []):
                if version["version"] == abs_version:
                    version_id = version["id"]
                    break
            conv_hero = convert_v4_version_to_v3(hero_version)
            conv_hero["version_id"] = version_id
            versions.append(conv_hero)

    return versions


def get_asset_by_id(project_name, asset_id, fields=None):
    assets = get_assets(
        project_name, asset_ids=[asset_id], fields=fields
    )
    for asset in assets:
        return asset
    return None


def get_asset_by_name(project_name, asset_name, fields=None):
    assets = get_assets(
        project_name, asset_names=[asset_name], fields=fields
    )
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
        return

    active = True
    if archived:
        active = None

    con = get_server_api_connection()
    fields = folder_fields_v3_to_v4(fields, con)
    kwargs = dict(
        folder_ids=asset_ids,
        folder_names=asset_names,
        parent_ids=parent_ids,
        active=active,
        fields=fields
    )

    if fields is None or "tasks" in fields:
        folders = get_folders_with_tasks(con, project_name, **kwargs)

    else:
        folders = con.get_folders(project_name, **kwargs)

    for folder in folders:
        yield convert_v4_folder_to_v3(folder, project_name)


def get_archived_assets(
    project_name,
    asset_ids=None,
    asset_names=None,
    parent_ids=None,
    fields=None
):
    return get_assets(
        project_name,
        asset_ids,
        asset_names,
        parent_ids,
        True,
        fields
    )


def get_asset_ids_with_subsets(project_name, asset_ids=None):
    con = get_server_api_connection()
    return con.get_folder_ids_with_products(project_name, asset_ids)


def get_subset_by_id(project_name, subset_id, fields=None):
    subsets = get_subsets(
        project_name, subset_ids=[subset_id], fields=fields
    )
    for subset in subsets:
        return subset
    return None


def get_subset_by_name(project_name, subset_name, asset_id, fields=None):
    subsets = get_subsets(
        project_name,
        subset_names=[subset_name],
        asset_ids=[asset_id],
        fields=fields
    )
    for subset in subsets:
        return subset
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
        fields=fields
    )


def get_subset_families(project_name, subset_ids=None):
    con = get_server_api_connection()
    return con.get_product_type_names(project_name, subset_ids)


def get_version_by_id(project_name, version_id, fields=None):
    versions = get_versions(
        project_name,
        version_ids=[version_id],
        fields=fields,
        hero=True
    )
    for version in versions:
        return version
    return None


def get_version_by_name(project_name, version, subset_id, fields=None):
    versions = get_versions(
        project_name,
        subset_ids=[subset_id],
        versions=[version],
        fields=fields
    )
    for version in versions:
        return version
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
    for version in versions:
        return version
    return None


def get_hero_version_by_subset_id(
    project_name, subset_id, fields=None
):
    versions = get_hero_versions(
        project_name,
        subset_ids=[subset_id],
        fields=fields
    )
    for version in versions:
        return version
    return None


def get_hero_versions(
    project_name, subset_ids=None, version_ids=None, fields=None
):
    return _get_versions(
        project_name,
        version_ids=version_ids,
        subset_ids=subset_ids,
        hero=True,
        standard=False,
        fields=fields
    )


def get_last_versions(project_name, subset_ids, active=None, fields=None):
    if fields:
        fields = set(fields)
        fields.add("parent")

    versions = _get_versions(
        project_name,
        subset_ids=subset_ids,
        latest=True,
        hero=False,
        active=active,
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
        hero=False,
        fields=fields
    )
    if not versions:
        return None
    return versions[0]


def get_last_version_by_subset_name(
    project_name,
    subset_name,
    asset_id=None,
    asset_name=None,
    fields=None
):
    if not asset_id and not asset_name:
        return None

    if not asset_id:
        asset = get_asset_by_name(
            project_name, asset_name, fields=["_id"]
        )
        if not asset:
            return None
        asset_id = asset["_id"]

    subset = get_subset_by_name(
        project_name, subset_name, asset_id, fields=["_id"]
    )
    if not subset:
        return None
    return get_last_version_by_subset_id(
        project_name, subset["_id"], fields=fields
    )


def get_output_link_versions(project_name, version_id, fields=None):
    if not version_id:
        return []

    con = get_server_api_connection()
    version_links = con.get_version_links(
        project_name, version_id, link_direction="out")

    version_ids = {
        link["entityId"]
        for link in version_links
        if link["entityType"] == "version"
    }
    if not version_ids:
        return []

    return get_versions(project_name, version_ids=version_ids, fields=fields)


def version_is_latest(project_name, version_id):
    con = get_server_api_connection()
    return con.version_is_latest(project_name, version_id)


def get_representation_by_id(project_name, representation_id, fields=None):
    representations = get_representations(
        project_name,
        representation_ids=[representation_id],
        fields=fields
    )
    for representation in representations:
        return representation
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
    for representation in representations:
        return representation
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
        return

    if archived and not standard:
        active = False
    elif not archived and standard:
        active = True
    else:
        active = None

    con = get_server_api_connection()
    fields = representation_fields_v3_to_v4(fields, con)
    if fields and active is not None:
        fields.add("active")

    representations = con.get_representations(
        project_name,
        representation_ids,
        representation_names,
        version_ids,
        names_by_version_ids,
        active,
        fields=fields
    )
    for representation in representations:
        yield convert_v4_representation_to_v3(representation)


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
    con = get_server_api_connection()
    parents_by_repre_id = con.get_representations_parents(project_name,
                                                          repre_ids)
    folder_ids = set()
    for parents in parents_by_repre_id .values():
        folder_ids.add(parents[2]["id"])

    tasks_by_folder_id = {}

    new_parents = {}
    for repre_id, parents in parents_by_repre_id .items():
        version, subset, folder, project = parents
        folder_tasks = tasks_by_folder_id.get(folder["id"]) or {}
        folder["tasks"] = folder_tasks
        new_parents[repre_id] = (
            convert_v4_version_to_v3(version),
            convert_v4_subset_to_v3(subset),
            convert_v4_folder_to_v3(folder, project_name),
            project
        )
    return new_parents


def get_archived_representations(
    project_name,
    representation_ids=None,
    representation_names=None,
    version_ids=None,
    context_filters=None,
    names_by_version_ids=None,
    fields=None
):
    return get_representations(
        project_name,
        representation_ids=representation_ids,
        representation_names=representation_names,
        version_ids=version_ids,
        context_filters=context_filters,
        names_by_version_ids=names_by_version_ids,
        archived=True,
        standard=False,
        fields=fields
    )


def get_thumbnail(
    project_name, thumbnail_id, entity_type, entity_id, fields=None
):
    """Receive thumbnail entity data.

    Args:
        project_name (str): Name of project where to look for queried entities.
        thumbnail_id (Union[str, ObjectId]): Id of thumbnail entity.
        entity_type (str): Type of entity for which the thumbnail should be
            received.
        entity_id (str): Id of entity for which the thumbnail should be
            received.
        fields (Iterable[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        None: If thumbnail with specified id was not found.
        Dict: Thumbnail entity data which can be reduced to specified 'fields'.
    """

    if not thumbnail_id or not entity_type or not entity_id:
        return None

    if entity_type == "asset":
        entity_type = "folder"

    elif entity_type == "hero_version":
        entity_type = "version"

    return {
        "_id": thumbnail_id,
        "type": "thumbnail",
        "schema": CURRENT_THUMBNAIL_SCHEMA,
        "data": {
            "entity_type": entity_type,
            "entity_id": entity_id
        }
    }


def get_thumbnails(project_name, thumbnail_contexts, fields=None):
    """Get thumbnail entities.

    Warning:
        This function is not OpenPype compatible. There is none usage of this
            function in codebase so there is nothing to convert. The previous
            implementation cannot be AYON compatible without entity types.
    """

    thumbnail_items = set()
    for thumbnail_context in thumbnail_contexts:
        thumbnail_id, entity_type, entity_id = thumbnail_context
        thumbnail_item = get_thumbnail(
            project_name, thumbnail_id, entity_type, entity_id
        )
        if thumbnail_item:
            thumbnail_items.add(thumbnail_item)
    return list(thumbnail_items)


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

    if src_type == "version":
        version = get_version_by_id(
            project_name, src_id, fields=["data.thumbnail_id"]
        ) or {}
        return version.get("data", {}).get("thumbnail_id")

    if src_type == "asset":
        asset = get_asset_by_id(
            project_name, src_id, fields=["data.thumbnail_id"]
        ) or {}
        return asset.get("data", {}).get("thumbnail_id")

    return None


def get_workfile_info(
    project_name, asset_id, task_name, filename, fields=None
):
    if not asset_id or not task_name or not filename:
        return None

    con = get_server_api_connection()
    task = con.get_task_by_name(
        project_name, asset_id, task_name, fields=["id", "name", "folderId"]
    )
    if not task:
        return None

    fields = workfile_info_fields_v3_to_v4(fields)

    for workfile_info in con.get_workfiles_info(
        project_name, task_ids=[task["id"]], fields=fields
    ):
        if workfile_info["name"] == filename:
            return convert_v4_workfile_info_to_v3(workfile_info, task)
    return None
