"""Unclear if these will have public functions like these.

Goal is that most of functions here are called on (or with) an object
that has project name as a context (e.g. on 'ProjectEntity'?).

+ We will need more specific functions doing wery specific queires really fast.
"""

import os
import collections

import six
from bson.objectid import ObjectId

from openpype.lib.mongo import OpenPypeMongoConnection


def _get_project_connection(project_name=None):
    db_name = os.environ.get("AVALON_DB") or "avalon"
    mongodb = OpenPypeMongoConnection.get_mongo_client()[db_name]
    if project_name:
        return mongodb[project_name]
    return mongodb


def _prepare_fields(fields):
    if not fields:
        return None

    output = {
        field: True
        for field in fields
    }
    if "_id" not in output:
        output["_id"] = True
    return output


def _convert_id(in_id):
    if isinstance(in_id, six.string_types):
        return ObjectId(in_id)
    return in_id


def _convert_ids(in_ids):
    _output = set()
    for in_id in in_ids:
        if in_id is not None:
            _output.add(_convert_id(in_id))
    return list(_output)


def get_projects(active=True, inactive=False, fields=None):
    mongodb = _get_project_connection()
    for project_name in mongodb.collection_names():
        if project_name in ("system.indexes",):
            continue
        project_doc = get_project(
            project_name, active=active, inactive=inactive, fields=fields
        )
        if project_doc is not None:
            yield project_doc


def get_project(project_name, active=True, inactive=False, fields=None):
    # Skip if both are disabled
    if not active and not inactive:
        return None

    query_filter = {"type": "project"}
    # Keep query untouched if both should be available
    if active and inactive:
        pass

    # Add filter to keep only active
    elif active:
        query_filter["$or"] = [
            {"data.active": {"$exists": False}},
            {"data.active": True},
        ]

    # Add filter to keep only inactive
    elif inactive:
        query_filter["$or"] = [
            {"data.active": {"$exists": False}},
            {"data.active": False},
        ]

    conn = _get_project_connection(project_name)
    return conn.find_one(query_filter, _prepare_fields(fields))


def get_asset_by_id(project_name, asset_id, fields=None):
    """Receive asset data by it's id.

    Args:
        project_name (str): Name of project where to look for queried entities.
        asset_id (str|ObjectId): Asset's id.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        dict: Asset entity data.
        None: Asset was not found by id.
    """

    asset_id = _convert_id(asset_id)
    if not asset_id:
        return None

    query_filter = {"type": "asset", "_id": asset_id}
    conn = _get_project_connection(project_name)
    return conn.find_one(query_filter, _prepare_fields(fields))


def get_asset_by_name(project_name, asset_name, fields=None):
    """Receive asset data by it's name.

    Args:
        project_name (str): Name of project where to look for queried entities.
        asset_name (str): Asset's name.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        dict: Asset entity data.
        None: Asset was not found by name.
    """

    if not asset_name:
        return None

    query_filter = {"type": "asset", "name": asset_name}
    conn = _get_project_connection(project_name)
    return conn.find_one(query_filter, _prepare_fields(fields))


def get_assets(
    project_name, asset_ids=None, asset_names=None, archived=False, fields=None
):
    """Assets for specified project by passed filters.

    Passed filters (ids and names) are always combined so all conditions must
    match.

    To receive all assets from project just keep filters empty.

    Args:
        project_name (str): Name of project where to look for queried entities.
        asset_ids (list[str, ObjectId]): Asset ids that should be found.
        asset_names (list[str]): Name assets that should be found.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        Cursor: Query cursor as iterable which returns asset documents matching
            passed filters.
    """

    asset_types = ["asset"]
    if archived:
        asset_types.append("archived_asset")

    if len(asset_types) == 1:
        query_filter = {"type": asset_types[0]}
    else:
        query_filter = {"type": {"$in": asset_types}}

    if asset_ids is not None:
        asset_ids = _convert_ids(asset_ids)
        if not asset_ids:
            return []
        query_filter["_id"] = {"$in": asset_ids}

    if asset_names is not None:
        if not asset_names:
            return []
        query_filter["name"] = {"$in": list(asset_names)}

    conn = _get_project_connection(project_name)

    return conn.find(query_filter, _prepare_fields(fields))


def get_asset_ids_with_subsets(project_name, asset_ids=None):
    """Find out which assets have existing subsets.

    Args:
        project_name (str): Name of project where to look for queried entities.
        asset_ids (list[str|ObjectId]): Look only for entered asset ids.

    Returns:
        List[ObjectId]: Asset ids that have existing subsets.
    """

    subset_query = {
        "type": "subset"
    }
    if asset_ids is not None:
        asset_ids = _convert_ids(asset_ids)
        if not asset_ids:
            return []
        subset_query["parent"] = {"$in": asset_ids}

    conn = _get_project_connection(project_name)
    result = conn.aggregate([
        {
            "$match": subset_query
        },
        {
            "$group": {
                "_id": "$parent",
                "count": {"$sum": 1}
            }
        }
    ])
    asset_ids_with_subsets = []
    for item in result:
        asset_id = item["_id"]
        count = item["count"]
        if count > 0:
            asset_ids_with_subsets.append(asset_id)
    return asset_ids_with_subsets


def get_subset_by_id(project_name, subset_id, fields=None):
    """Single subset document by it's id.

    Args:
        project_name (str): Name of project where to look for queried entities.
        subset_id (ObjectId): Id of subset which should be found.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        None: If subset with specified filters was not found.
        Dict: Subset document which can be reduced to specified 'fields'.
    """

    subset_id = _convert_id(subset_id)
    if not subset_id:
        return None

    query_filters = {"type": "subset", "_id": subset_id}
    conn = _get_project_connection(project_name)
    return conn.find_one(query_filters, _prepare_fields(fields))


def get_subset_by_name(project_name, subset_name, asset_id, fields=None):
    """Single subset document by subset name and it's version id.

    Args:
        project_name (str): Name of project where to look for queried entities.
        subset_name (str): Name of subset.
        asset_id (str|ObjectId): Id of parent asset.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        None: If subset with specified filters was not found.
        Dict: Subset document which can be reduced to specified 'fields'.
    """

    if not subset_name:
        return None

    asset_id = _convert_id(asset_id)
    if not asset_id:
        return None

    query_filters = {
        "type": "subset",
        "name": subset_name,
        "parent": asset_id
    }
    conn = _get_project_connection(project_name)
    return conn.find_one(query_filters, _prepare_fields(fields))


def get_subsets(
    project_name,
    asset_ids=None,
    subset_ids=None,
    subset_names=None,
    archived=False,
    fields=None
):
    subset_types = ["subset"]
    if archived:
        subset_types.append("archived_subset")

    if len(subset_types) == 1:
        query_filter = {"type": subset_types[0]}
    else:
        query_filter = {"type": {"$in": subset_types}}

    if asset_ids is not None:
        asset_ids = _convert_ids(asset_ids)
        if not asset_ids:
            return []
        query_filter["parent"] = {"$in": asset_ids}

    if subset_ids is not None:
        subset_ids = _convert_ids(subset_ids)
        if not subset_ids:
            return []
        query_filter["_id"] = {"$in": subset_ids}

    if subset_names is not None:
        if not subset_names:
            return []
        query_filter["name"] = {"$in": list(subset_names)}

    conn = _get_project_connection(project_name)
    return conn.find(query_filter, _prepare_fields(fields))


def get_subset_families(project_name, subset_ids=None):
    subset_filter = {
        "type": "subset"
    }
    if subset_ids is not None:
        if not subset_ids:
            return set()
        subset_filter["_id"] = {"$in": list(subset_ids)}

    conn = _get_project_connection(project_name)
    result = list(conn.aggregate([
        {"$match": subset_filter},
        {"$project": {
            "family": {"$arrayElemAt": ["$data.families", 0]}
        }},
        {"$group": {
            "_id": "family_group",
            "families": {"$addToSet": "$family"}
        }}
    ]))
    if result:
        return set(result[0]["families"])
    return set()


def get_version_by_name(project_name, subset_id, version, fields=None):
    conn = _get_project_connection(project_name)
    query_filter = {
        "type": "version",
        "parent": _convert_id(subset_id),
        "name": version
    }
    return conn.find_one(query_filter, _prepare_fields(fields))


def get_version(project_name, version_id, fields=None):
    if not version_id:
        return None
    conn = _get_project_connection(project_name)
    query_filter = {
        "type": {"$in": ["version", "hero_version"]},
        "_id": _convert_id(version_id)
    }
    return conn.find_one(query_filter, _prepare_fields(fields))


def _get_versions(
    project_name,
    subset_ids=None,
    version_ids=None,
    standard=True,
    hero=False,
    fields=None
):
    version_types = []
    if standard:
        version_types.append("version")

    if hero:
        version_types.append("hero_version")

    if not version_types:
        return []
    elif len(version_types) == 1:
        query_filter = {"type": version_types[0]}
    else:
        query_filter = {"type": {"$in": version_types}}

    if subset_ids is not None:
        subset_ids = _convert_ids(subset_ids)
        if not subset_ids:
            return []
        query_filter["parent"] = {"$in": subset_ids}

    if version_ids is not None:
        version_ids = _convert_ids(version_ids)
        if not version_ids:
            return []
        query_filter["_id"] = {"$in": version_ids}

    conn = _get_project_connection(project_name)

    return conn.find(query_filter, _prepare_fields(fields))


def get_versions(
    project_name,
    subset_ids=None,
    version_ids=None,
    hero=False,
    fields=None
):
    return _get_versions(
        project_name,
        subset_ids,
        version_ids,
        standard=True,
        hero=hero,
        fields=fields
    )


def get_hero_version(
    project_name,
    subset_id=None,
    version_id=None,
    fields=None
):
    if not subset_id and not version_id:
        return None

    subset_ids = None
    if subset_id is not None:
        subset_ids = [subset_id]

    version_ids = None
    if version_id is not None:
        version_ids = [version_id]

    versions = list(_get_versions(
        project_name,
        subset_ids=subset_ids,
        version_ids=version_ids,
        standard=False,
        hero=True,
        fields=fields
    ))
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
        subset_ids,
        version_ids,
        standard=False,
        hero=True,
        fields=fields
    )


def get_version_links(project_name, version_id, fields=None):
    conn = _get_project_connection(project_name)
    # Does make sense to look for hero versions?
    query_filter = {
        "type": "version",
        "data.inputLinks.input": _convert_id(version_id)
    }
    return conn.find(query_filter, _prepare_fields(fields))


def get_last_versions(project_name, subset_ids, fields=None):
    """Retrieve all latest versions for entered subset_ids.

    Args:
        subset_ids (list): List of subset ids.

    Returns:
        dict: Key is subset id and value is last version name.
    """

    subset_ids = _convert_ids(subset_ids)
    if not subset_ids:
        return {}

    _pipeline = [
        # Find all versions of those subsets
        {"$match": {
            "type": "version",
            "parent": {"$in": subset_ids}
        }},
        # Sorting versions all together
        {"$sort": {"name": 1}},
        # Group them by "parent", but only take the last
        {"$group": {
            "_id": "$parent",
            "_version_id": {"$last": "$_id"}
        }}
    ]

    conn = _get_project_connection(project_name)
    version_ids = [
        doc["_version_id"]
        for doc in conn.aggregate(_pipeline)
    ]
    version_docs = get_versions(
        project_name, version_ids=version_ids, fields=fields
    )

    return {
        version_doc["parent"]: version_doc
        for version_doc in version_docs
    }


def get_last_version_for_subset(
    project_name, subset_id=None, subset_name=None, asset_id=None, fields=None
):
    subset_doc = get_subset(
        project_name,
        subset_id=subset_id,
        subset_name=subset_name,
        asset_id=asset_id,
        fields=["_id"]
    )
    if not subset_doc:
        return None
    subset_id = subset_doc["_id"]
    last_versions = get_last_versions(
        project_name, subset_ids=[subset_id], fields=fields
    )
    return last_versions.get(subset_id)


def get_representation(
    project_name,
    representation_id=None,
    representation_name=None,
    version_id=None,
    fields=None
):
    if not representation_id:
        if not representation_name or not version_id:
            return None

    repre_types = ["representation", "archived_representations"]
    query_filter = {
        "type": {"$in": repre_types}
    }
    if representation_id is not None:
        query_filter["_id"] = _convert_id(representation_id)

    if representation_name is not None:
        query_filter["name"] = representation_name

    if version_id is not None:
        query_filter["parent"] = version_id

    conn = _get_project_connection(project_name)

    return conn.find_one(query_filter, _prepare_fields(fields))


def get_representation_by_name(
    project_name, representation_name, version_id, fields=None
):
    if not version_id or not representation_name:
        return None
    repre_types = ["representation", "archived_representations"]
    query_filter = {
        "type": {"$in": repre_types},
        "name": representation_name,
        "parent": _convert_id(version_id)
    }

    conn = _get_project_connection(project_name)

    return conn.find_one(query_filter, _prepare_fields(fields))


def get_representations(
    project_name,
    representation_ids=None,
    representation_names=None,
    version_ids=None,
    extensions=None,
    names_by_version_ids=None,
    check_site_name=False,
    archived=False,
    fields=None
):
    repre_types = ["representation"]
    if archived:
        repre_types.append("archived_representations")
    if len(repre_types) == 1:
        query_filter = {"type": repre_types[0]}
    else:
        query_filter = {"type": {"$in": repre_types}}

    if check_site_name:
        query_filter["files.site.name"] = {"$exists": True}

    if representation_ids is not None:
        representation_ids = _convert_ids(representation_ids)
        if not representation_ids:
            return []
        query_filter["_id"] = {"$in": representation_ids}

    if representation_names is not None:
        if not representation_names:
            return []
        query_filter["name"] = {"$in": list(representation_names)}

    if version_ids is not None:
        version_ids = _convert_ids(version_ids)
        if not version_ids:
            return []
        query_filter["parent"] = {"$in": version_ids}

    if extensions is not None:
        if not extensions:
            return []
        query_filter["context.ext"] = {"$in": list(extensions)}

    if names_by_version_ids is not None:
        or_query = []
        for version_id, names in names_by_version_ids.items():
            if version_id and names:
                or_query.append({
                    "parent": _convert_id(version_id),
                    "name": {"$in": list(names)}
                })
        if not or_query:
            return []
        query_filter["$or"] = or_query

    conn = _get_project_connection(project_name)

    return conn.find(query_filter, _prepare_fields(fields))


def get_representations_parents(project_name, representations):
    repres_by_version_id = collections.defaultdict(list)
    versions_by_version_id = {}
    versions_by_subset_id = collections.defaultdict(list)
    subsets_by_subset_id = {}
    subsets_by_asset_id = collections.defaultdict(list)
    for representation in representations:
        repre_id = representation["_id"]
        version_id = representation["parent"]
        repres_by_version_id[version_id].append(representation)

    versions = get_versions(
        project_name, version_ids=repres_by_version_id.keys()
    )
    for version in versions:
        version_id = version["_id"]
        subset_id = version["parent"]
        versions_by_version_id[version_id] = version
        versions_by_subset_id[subset_id].append(version)

    subsets = get_subsets(
        project_name, subset_ids=versions_by_subset_id.keys()
    )
    for subset in subsets:
        subset_id = subset["_id"]
        asset_id = subset["parent"]
        subsets_by_subset_id[subset_id] = subset
        subsets_by_asset_id[asset_id].append(subset)

    assets = get_assets(project_name, asset_ids=subsets_by_asset_id.keys())
    assets_by_id = {
        asset["_id"]: asset
        for asset in assets
    }

    project = get_project(project_name)

    output = {}
    for version_id, representations in repres_by_version_id.items():
        asset = None
        subset = None
        version = versions_by_version_id.get(version_id)
        if version:
            subset_id = version["parent"]
            subset = subsets_by_subset_id.get(subset_id)
            if subset:
                asset_id = subset["parent"]
                asset = assets_by_id.get(asset_id)

        for representation in representations:
            repre_id = representation["_id"]
            output[repre_id] = (version, subset, asset, project)
    return output


def get_representation_parents(project_name, representation):
    if not representation:
        return None

    repre_id = representation["_id"]
    parents_by_repre_id = get_representations(project_name, [representation])
    return parents_by_repre_id.get(repre_id)


def get_thumbnail_id_from_source(project_name, src_type, src_id):
    if not src_type or not src_id:
        return None

    query_filter = {"_id": _convert_id(src_id)}

    conn = _get_project_connection(project_name)
    src_doc = conn.find_one(query_filter, {"data.thumbnail_id"})
    if src_doc:
        return src_doc.get("data", {}).get("thumbnail_id")
    return None


def get_thumbnail(project_name, thumbnail_id, fields=None):
    if not thumbnail_id:
        return None
    query_filter = {"type": "thumbnail", "_id": _convert_id(thumbnail_id)}
    conn = _get_project_connection(project_name)
    return conn.find(query_filter, _prepare_fields(fields))


"""
Custom data storage:
- Webpublisher - jobs
- Ftrack - events

openpype/tools/assetlinks/widgets.py
- SimpleLinkView
    Query:
    - get_versions
    - get_subsets
    - get_assets
    - get_version_links

openpype/tools/creator/window.py
- CreatorWindow
    Query:
    - get_asset
    - get_subsets

openpype/tools/launcher/models.py
- LauncherModel
    Query:
    - get_project
    - get_assets

openpype/tools/libraryloader/app.py
- LibraryLoaderWindow
    Query:
    - get_project

openpype/tools/loader/app.py
- LoaderWindow
    Query:
    - get_project
- show
    Query:
    - get_projects

openpype/tools/loader/model.py
- SubsetsModel
    Query:
    - get_assets
    - get_subsets
    - get_last_versions
    - get_versions
    - get_hero_versions
    - get_version_by_name
- RepresentationModel
    Query:
    - get_representations
    - sync server specific queries (separated into multiple functions?)
        - NOT REPLACED

openpype/tools/loader/widgets.py
- FamilyModel
    Query:
    - get_subset_families
- VersionTextEdit
    Query:
    - get_subset
    - get_version
- SubsetWidget
    Query:
    - get_subsets
    - get_representations
- RepresentationWidget
    Query:
    - get_subsets
    - get_versions
    - get_representations
- ThumbnailWidget
    Query:
    - get_thumbnail_id_from_source
    - get_thumbnail

openpype/tools/mayalookassigner/app.py
- MayaLookAssignerWindow
    Query:
    - get_last_version_for_subset

openpype/tools/mayalookassigner/commands.py
- create_items_from_nodes
    Query:
    - get_asset

openpype/tools/mayalookassigner/vray_proxies.py
- get_look_relationships
    Query:
    - get_representation_by_name
- load_look
    Query:
    - get_representation_by_name
- vrayproxy_assign_look
    Query:
    - get_last_version_for_subset

openpype/tools/project_manager/project_manager/model.py
- HierarchyModel
    Query:
    - get_asset_ids_with_subsets
    - get_project
    - get_assets

openpype/tools/project_manager/project_manager/view.py
- ProjectDocCache
    Query:
    - get_project

openpype/tools/project_manager/project_manager/widgets.py
- CreateProjectDialog
    Query:
    - get_projects

openpype/tools/publisher/widgets/create_dialog.py
- CreateDialog
    Query:
    - get_asset
    - get_subsets

openpype/tools/publisher/control.py
- AssetDocsCache
    Query:
    - get_assets

openpype/tools/sceneinventory/model.py
- InventoryModel
    Query:
    - get_asset
    - get_subset
    - get_version
    - get_last_version_for_subset
    - get_representation

openpype/tools/sceneinventory/switch_dialog.py
- SwitchAssetDialog
    Query:
    - get_asset
    - get_assets
    - get_subset
    - get_subsets
    - get_versions
    - get_hero_versions
    - get_last_versions
    - get_representations

openpype/tools/sceneinventory/view.py
- SceneInventoryView
    Query:
    - get_version
    - get_versions
    - get_hero_versions
    - get_representation
    - get_representations

openpype/tools/standalonepublish/widgets/model_asset.py
- AssetModel
    Query:
    - get_assets

openpype/tools/standalonepublish/widgets/widget_asset.py
- AssetWidget
    Query:
    - get_project
    - get_asset

openpype/tools/standalonepublish/widgets/widget_family.py
- FamilyWidget
    Query:
    - get_asset
    - get_subset
    - get_subsets
    - get_last_version_for_subset

openpype/tools/standalonepublish/app.py
- Window
    Query:
    - get_asset

openpype/tools/texture_copy/app.py
- TextureCopy
    Query:
    - get_project
    - get_asset

openpype/tools/workfiles/files_widget.py
- FilesWidget
    Query:
    - get_asset

openpype/tools/workfiles/model.py
- PublishFilesModel
    Query:
    - get_subsets
    - get_versions
    - get_representations

openpype/tools/workfiles/save_as_dialog.py
- build_workfile_data
    Query:
    - get_project
    - get_asset

openpype/tools/workfiles/window.py
- Window
    Query:
    - get_asset

openpype/tools/utils/assets_widget.py
- AssetModel
    Query:
    - get_project
    - get_assets

openpype/tools/utils/delegates.py
- VersionDelegate
    Query:
    - get_versions
    - get_hero_versions

openpype/tools/utils/lib.py
- GroupsConfig
    Query:
    - get_project
- FamilyConfigCache
    Query:
    - get_asset

openpype/tools/utils/tasks_widget.py
- TasksModel
    Query:
    - get_project
    - get_asset
"""
