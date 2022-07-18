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


def _get_project_database():
    db_name = os.environ.get("AVALON_DB") or "avalon"
    return OpenPypeMongoConnection.get_mongo_client()[db_name]


def _get_project_connection(project_name):
    if not project_name:
        raise ValueError("Invalid project name {}".format(str(project_name)))
    return _get_project_database()[project_name]


def _prepare_fields(fields, required_fields=None):
    if not fields:
        return None

    output = {
        field: True
        for field in fields
    }
    if "_id" not in output:
        output["_id"] = True

    if required_fields:
        for key in required_fields:
            output[key] = True
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
    mongodb = _get_project_database()
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


def get_whole_project(project_name):
    """Receive all documents from project.

    Helper that can be used to get all document from whole project. For example
    for backups etc.

    Returns:
        Cursor: Query cursor as iterable which returns all documents from
            project collection.
    """

    conn = _get_project_connection(project_name)
    return conn.find({})


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


# NOTE this could be just public function?
# - any better variable name instead of 'standard'?
# - same approach can be used for rest of types
def _get_assets(
    project_name,
    asset_ids=None,
    asset_names=None,
    parent_ids=None,
    standard=True,
    archived=False,
    fields=None
):
    """Assets for specified project by passed filters.

    Passed filters (ids and names) are always combined so all conditions must
    match.

    To receive all assets from project just keep filters empty.

    Args:
        project_name (str): Name of project where to look for queried entities.
        asset_ids (list[str|ObjectId]): Asset ids that should be found.
        asset_names (list[str]): Name assets that should be found.
        parent_ids (list[str|ObjectId]): Parent asset ids.
        standard (bool): Query standart assets (type 'asset').
        archived (bool): Query archived assets (type 'archived_asset').
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        Cursor: Query cursor as iterable which returns asset documents matching
            passed filters.
    """

    asset_types = []
    if standard:
        asset_types.append("asset")
    if archived:
        asset_types.append("archived_asset")

    if not asset_types:
        return []

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

    if parent_ids is not None:
        parent_ids = _convert_ids(parent_ids)
        if not parent_ids:
            return []
        query_filter["data.visualParent"] = {"$in": parent_ids}

    conn = _get_project_connection(project_name)

    return conn.find(query_filter, _prepare_fields(fields))


def get_assets(
    project_name,
    asset_ids=None,
    asset_names=None,
    parent_ids=None,
    archived=False,
    fields=None
):
    """Assets for specified project by passed filters.

    Passed filters (ids and names) are always combined so all conditions must
    match.

    To receive all assets from project just keep filters empty.

    Args:
        project_name (str): Name of project where to look for queried entities.
        asset_ids (list[str|ObjectId]): Asset ids that should be found.
        asset_names (list[str]): Name assets that should be found.
        parent_ids (list[str|ObjectId]): Parent asset ids.
        archived (bool): Add also archived assets.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        Cursor: Query cursor as iterable which returns asset documents matching
            passed filters.
    """

    return _get_assets(
        project_name,
        asset_ids,
        asset_names,
        parent_ids,
        True,
        archived,
        fields
    )


def get_archived_assets(
    project_name,
    asset_ids=None,
    asset_names=None,
    parent_ids=None,
    fields=None
):
    """Archived assets for specified project by passed filters.

    Passed filters (ids and names) are always combined so all conditions must
    match.

    To receive all archived assets from project just keep filters empty.

    Args:
        project_name (str): Name of project where to look for queried entities.
        asset_ids (list[str|ObjectId]): Asset ids that should be found.
        asset_names (list[str]): Name assets that should be found.
        parent_ids (list[str|ObjectId]): Parent asset ids.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        Cursor: Query cursor as iterable which returns asset documents matching
            passed filters.
    """

    return _get_assets(
        project_name, asset_ids, asset_names, parent_ids, False, True, fields
    )


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
    """Single subset entity data by it's id.

    Args:
        project_name (str): Name of project where to look for queried entities.
        subset_id (str|ObjectId): Id of subset which should be found.
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
    """Single subset entity data by it's name and it's version id.

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
    subset_ids=None,
    subset_names=None,
    asset_ids=None,
    names_by_asset_ids=None,
    archived=False,
    fields=None
):
    """Subset entities data from one project filtered by entered filters.

    Filters are additive (all conditions must pass to return subset).

    Args:
        project_name (str): Name of project where to look for queried entities.
        subset_ids (list[str|ObjectId]): Subset ids that should be queried.
            Filter ignored if 'None' is passed.
        subset_names (list[str]): Subset names that should be queried.
            Filter ignored if 'None' is passed.
        asset_ids (list[str|ObjectId]): Asset ids under which should look for
            the subsets. Filter ignored if 'None' is passed.
        names_by_asset_ids (dict[ObjectId, list[str]]): Complex filtering
            using asset ids and list of subset names under the asset.
        archived (bool): Look for archived subsets too.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        Cursor: Iterable cursor yielding all matching subsets.
    """

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

    if names_by_asset_ids is not None:
        or_query = []
        for asset_id, names in names_by_asset_ids.items():
            if asset_id and names:
                or_query.append({
                    "parent": _convert_id(asset_id),
                    "name": {"$in": list(names)}
                })
        if not or_query:
            return []
        query_filter["$or"] = or_query

    conn = _get_project_connection(project_name)
    return conn.find(query_filter, _prepare_fields(fields))


def get_subset_families(project_name, subset_ids=None):
    """Set of main families of subsets.

    Args:
        project_name (str): Name of project where to look for queried entities.
        subset_ids (list[str|ObjectId]): Subset ids that should be queried.
            All subsets from project are used if 'None' is passed.

    Returns:
         set[str]: Main families of matching subsets.
    """

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


def get_version_by_id(project_name, version_id, fields=None):
    """Single version entity data by it's id.

    Args:
        project_name (str): Name of project where to look for queried entities.
        version_id (str|ObjectId): Id of version which should be found.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        None: If version with specified filters was not found.
        Dict: Version document which can be reduced to specified 'fields'.
    """

    version_id = _convert_id(version_id)
    if not version_id:
        return None

    query_filter = {
        "type": {"$in": ["version", "hero_version"]},
        "_id": version_id
    }
    conn = _get_project_connection(project_name)
    return conn.find_one(query_filter, _prepare_fields(fields))


def get_version_by_name(project_name, version, subset_id, fields=None):
    """Single version entity data by it's name and subset id.

    Args:
        project_name (str): Name of project where to look for queried entities.
        version (int): name of version entity (it's version).
        subset_id (str|ObjectId): Id of version which should be found.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        None: If version with specified filters was not found.
        Dict: Version document which can be reduced to specified 'fields'.
    """

    subset_id = _convert_id(subset_id)
    if not subset_id:
        return None

    conn = _get_project_connection(project_name)
    query_filter = {
        "type": "version",
        "parent": subset_id,
        "name": version
    }
    return conn.find_one(query_filter, _prepare_fields(fields))


def _get_versions(
    project_name,
    subset_ids=None,
    version_ids=None,
    versions=None,
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

    if versions is not None:
        versions = list(versions)
        if not versions:
            return []

        if len(versions) == 1:
            query_filter["name"] = versions[0]
        else:
            query_filter["name"] = {"$in": versions}

    conn = _get_project_connection(project_name)

    return conn.find(query_filter, _prepare_fields(fields))


def get_versions(
    project_name,
    version_ids=None,
    subset_ids=None,
    versions=None,
    hero=False,
    fields=None
):
    """Version entities data from one project filtered by entered filters.

    Filters are additive (all conditions must pass to return subset).

    Args:
        project_name (str): Name of project where to look for queried entities.
        version_ids (list[str|ObjectId]): Version ids that will be queried.
            Filter ignored if 'None' is passed.
        subset_ids (list[str]): Subset ids that will be queried.
            Filter ignored if 'None' is passed.
        versions (list[int]): Version names (as integers).
            Filter ignored if 'None' is passed.
        hero (bool): Look also for hero versions.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        Cursor: Iterable cursor yielding all matching versions.
    """

    return _get_versions(
        project_name,
        subset_ids,
        version_ids,
        versions,
        standard=True,
        hero=hero,
        fields=fields
    )


def get_hero_version_by_subset_id(project_name, subset_id, fields=None):
    """Hero version by subset id.

    Args:
        project_name (str): Name of project where to look for queried entities.
        subset_id (str|ObjectId): Subset id under which is hero version.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        None: If hero version for passed subset id does not exists.
        Dict: Hero version entity data.
    """

    subset_id = _convert_id(subset_id)
    if not subset_id:
        return None

    versions = list(_get_versions(
        project_name,
        subset_ids=[subset_id],
        standard=False,
        hero=True,
        fields=fields
    ))
    if versions:
        return versions[0]
    return None


def get_hero_version_by_id(project_name, version_id, fields=None):
    """Hero version by it's id.

    Args:
        project_name (str): Name of project where to look for queried entities.
        version_id (str|ObjectId): Hero version id.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        None: If hero version with passed id was not found.
        Dict: Hero version entity data.
    """

    version_id = _convert_id(version_id)
    if not version_id:
        return None

    versions = list(_get_versions(
        project_name,
        version_ids=[version_id],
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
    """Hero version entities data from one project filtered by entered filters.

    Args:
        project_name (str): Name of project where to look for queried entities.
        subset_ids (list[str|ObjectId]): Subset ids for which should look for
            hero versions. Filter ignored if 'None' is passed.
        version_ids (list[str|ObjectId]): Hero version ids. Filter ignored if
            'None' is passed.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        Cursor|list: Iterable yielding hero versions matching passed filters.
    """

    return _get_versions(
        project_name,
        subset_ids,
        version_ids,
        standard=False,
        hero=True,
        fields=fields
    )


def get_output_link_versions(project_name, version_id, fields=None):
    """Versions where passed version was used as input.

    Question:
        Not 100% sure about the usage of the function so the name and docstring
            maybe does not match what it does?

    Args:
        project_name (str): Name of project where to look for queried entities.
        version_id (str|ObjectId): Version id which can be used as input link
            for other versions.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        Cursor|list: Iterable cursor yielding versions that are used as input
            links for passed version.
    """

    version_id = _convert_id(version_id)
    if not version_id:
        return []

    conn = _get_project_connection(project_name)
    # Does make sense to look for hero versions?
    query_filter = {
        "type": "version",
        "data.inputLinks.input": version_id
    }
    return conn.find(query_filter, _prepare_fields(fields))


def get_last_versions(project_name, subset_ids, fields=None):
    """Latest versions for entered subset_ids.

    Args:
        project_name (str): Name of project where to look for queried entities.
        subset_ids (list): List of subset ids.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        dict[ObjectId, int]: Key is subset id and value is last version name.
    """

    subset_ids = _convert_ids(subset_ids)
    if not subset_ids:
        return {}

    if fields is not None:
        fields = list(fields)
        if not fields:
            return {}

    # Avoid double query if only name and _id are requested
    name_needed = False
    limit_query = False
    if fields:
        fields_s = set(fields)
        if "name" in fields_s:
            name_needed = True
            fields_s.remove("name")

        for field in ("_id", "parent"):
            if field in fields_s:
                fields_s.remove(field)
        limit_query = len(fields_s) == 0

    group_item = {
        "_id": "$parent",
        "_version_id": {"$last": "$_id"}
    }
    # Add name if name is needed (only for limit query)
    if name_needed:
        group_item["name"] = {"$last": "$name"}

    aggregation_pipeline = [
        # Find all versions of those subsets
        {"$match": {
            "type": "version",
            "parent": {"$in": subset_ids}
        }},
        # Sorting versions all together
        {"$sort": {"name": 1}},
        # Group them by "parent", but only take the last
        {"$group": group_item}
    ]

    conn = _get_project_connection(project_name)
    aggregate_result = conn.aggregate(aggregation_pipeline)
    if limit_query:
        output = {}
        for item in aggregate_result:
            subset_id = item["_id"]
            item_data = {"_id": item["_version_id"], "parent": subset_id}
            if name_needed:
                item_data["name"] = item["name"]
            output[subset_id] = item_data
        return output

    version_ids = [
        doc["_version_id"]
        for doc in aggregate_result
    ]

    fields = _prepare_fields(fields, ["parent"])

    version_docs = get_versions(
        project_name, version_ids=version_ids, fields=fields
    )

    return {
        version_doc["parent"]: version_doc
        for version_doc in version_docs
    }


def get_last_version_by_subset_id(project_name, subset_id, fields=None):
    """Last version for passed subset id.

    Args:
        project_name (str): Name of project where to look for queried entities.
        subset_id (str|ObjectId): Id of version which should be found.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        None: If version with specified filters was not found.
        Dict: Version document which can be reduced to specified 'fields'.
    """

    subset_id = _convert_id(subset_id)
    if not subset_id:
        return None

    last_versions = get_last_versions(
        project_name, subset_ids=[subset_id], fields=fields
    )
    return last_versions.get(subset_id)


def get_last_version_by_subset_name(
    project_name, subset_name, asset_id=None, asset_name=None, fields=None
):
    """Last version for passed subset name under asset id/name.

    It is required to pass 'asset_id' or 'asset_name'. Asset id is recommended
    if is available.

    Args:
        project_name (str): Name of project where to look for queried entities.
        subset_name (str): Name of subset.
        asset_id (str|ObjectId): Asset id which is parent of passed
            subset name.
        asset_name (str): Asset name which is parent of passed subset name.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        None: If version with specified filters was not found.
        Dict: Version document which can be reduced to specified 'fields'.
    """

    if not asset_id and not asset_name:
        return None

    if not asset_id:
        asset_doc = get_asset_by_name(project_name, asset_name, fields=["_id"])
        if not asset_doc:
            return None
        asset_id = asset_doc["_id"]
    subset_doc = get_subset_by_name(
        project_name, subset_name, asset_id, fields=["_id"]
    )
    if not subset_doc:
        return None
    return get_last_version_by_subset_id(
        project_name, subset_doc["_id"], fields=fields
    )


def get_representation_by_id(project_name, representation_id, fields=None):
    """Representation entity data by it's id.

    Args:
        project_name (str): Name of project where to look for queried entities.
        representation_id (str|ObjectId): Representation id.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        None: If representation with specified filters was not found.
        Dict: Representation entity data which can be reduced
            to specified 'fields'.
    """

    if not representation_id:
        return None

    repre_types = ["representation", "archived_representation"]
    query_filter = {
        "type": {"$in": repre_types}
    }
    if representation_id is not None:
        query_filter["_id"] = _convert_id(representation_id)

    conn = _get_project_connection(project_name)

    return conn.find_one(query_filter, _prepare_fields(fields))


def get_representation_by_name(
    project_name, representation_name, version_id, fields=None
):
    """Representation entity data by it's name and it's version id.

    Args:
        project_name (str): Name of project where to look for queried entities.
        representation_name (str): Representation name.
        version_id (str|ObjectId): Id of parent version entity.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        None: If representation with specified filters was not found.
        Dict: Representation entity data which can be reduced
            to specified 'fields'.
    """

    version_id = _convert_id(version_id)
    if not version_id or not representation_name:
        return None
    repre_types = ["representation", "archived_representations"]
    query_filter = {
        "type": {"$in": repre_types},
        "name": representation_name,
        "parent": version_id
    }

    conn = _get_project_connection(project_name)
    return conn.find_one(query_filter, _prepare_fields(fields))


def _get_representations(
    project_name,
    representation_ids,
    representation_names,
    version_ids,
    extensions,
    names_by_version_ids,
    standard,
    archived,
    fields
):
    repre_types = []
    if standard:
        repre_types.append("representation")
    if archived:
        repre_types.append("archived_representation")

    if not repre_types:
        return []

    if len(repre_types) == 1:
        query_filter = {"type": repre_types[0]}
    else:
        query_filter = {"type": {"$in": repre_types}}

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


def get_representations(
    project_name,
    representation_ids=None,
    representation_names=None,
    version_ids=None,
    extensions=None,
    names_by_version_ids=None,
    archived=False,
    standard=True,
    fields=None
):
    """Representaion entities data from one project filtered by filters.

    Filters are additive (all conditions must pass to return subset).

    Args:
        project_name (str): Name of project where to look for queried entities.
        representation_ids (list[str|ObjectId]): Representation ids used as
            filter. Filter ignored if 'None' is passed.
        representation_names (list[str]): Representations names used as filter.
            Filter ignored if 'None' is passed.
        version_ids (list[str]): Subset ids used as parent filter. Filter
            ignored if 'None' is passed.
        extensions (list[str]): Filter by extension of main representation
            file (without dot).
        names_by_version_ids (dict[ObjectId, list[str]]): Complex filtering
            using version ids and list of names under the version.
        archived (bool): Output will also contain archived representations.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        Cursor: Iterable cursor yielding all matching representations.
    """

    return _get_representations(
        project_name=project_name,
        representation_ids=representation_ids,
        representation_names=representation_names,
        version_ids=version_ids,
        extensions=extensions,
        names_by_version_ids=names_by_version_ids,
        standard=True,
        archived=archived,
        fields=fields
    )


def get_archived_representations(
    project_name,
    representation_ids=None,
    representation_names=None,
    version_ids=None,
    extensions=None,
    names_by_version_ids=None,
    fields=None
):
    """Archived representaion entities data from project with applied filters.

    Filters are additive (all conditions must pass to return subset).

    Args:
        project_name (str): Name of project where to look for queried entities.
        representation_ids (list[str|ObjectId]): Representation ids used as
            filter. Filter ignored if 'None' is passed.
        representation_names (list[str]): Representations names used as filter.
            Filter ignored if 'None' is passed.
        version_ids (list[str]): Subset ids used as parent filter. Filter
            ignored if 'None' is passed.
        extensions (list[str]): Filter by extension of main representation
            file (without dot).
        names_by_version_ids (dict[ObjectId, list[str]]): Complex filtering
            using version ids and list of names under the version.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        Cursor: Iterable cursor yielding all matching representations.
    """

    return _get_representations(
        project_name=project_name,
        representation_ids=representation_ids,
        representation_names=representation_names,
        version_ids=version_ids,
        extensions=extensions,
        names_by_version_ids=names_by_version_ids,
        standard=False,
        archived=True,
        fields=fields
    )


def get_representations_parents(project_name, representations):
    """Prepare parents of representation entities.

    Each item of returned dictionary contains version, subset, asset
    and project in that order.

    Args:
        project_name (str): Name of project where to look for queried entities.
        representations (list[dict]): Representation entities with at least
            '_id' and 'parent' keys.

    Returns:
        dict[ObjectId, tuple]: Parents by representation id.
    """

    repres_by_version_id = collections.defaultdict(list)
    versions_by_version_id = {}
    versions_by_subset_id = collections.defaultdict(list)
    subsets_by_subset_id = {}
    subsets_by_asset_id = collections.defaultdict(list)
    output = {}
    for representation in representations:
        repre_id = representation["_id"]
        output[repre_id] = (None, None, None, None)
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
    """Prepare parents of representation entity.

    Each item of returned dictionary contains version, subset, asset
    and project in that order.

    Args:
        project_name (str): Name of project where to look for queried entities.
        representation (dict): Representation entities with at least
            '_id' and 'parent' keys.

    Returns:
        dict[ObjectId, tuple]: Parents by representation id.
    """

    if not representation:
        return None

    repre_id = representation["_id"]
    parents_by_repre_id = get_representations_parents(
        project_name, [representation]
    )
    return parents_by_repre_id[repre_id]


def get_thumbnail_id_from_source(project_name, src_type, src_id):
    """Receive thumbnail id from source entity.

    Args:
        project_name (str): Name of project where to look for queried entities.
        src_type (str): Type of source entity ('asset', 'version').
        src_id (str|objectId): Id of source entity.

    Returns:
        ObjectId: Thumbnail id assigned to entity.
        None: If Source entity does not have any thumbnail id assigned.
    """

    if not src_type or not src_id:
        return None

    query_filter = {"_id": _convert_id(src_id)}

    conn = _get_project_connection(project_name)
    src_doc = conn.find_one(query_filter, {"data.thumbnail_id"})
    if src_doc:
        return src_doc.get("data", {}).get("thumbnail_id")
    return None


def get_thumbnails(project_name, thumbnail_ids, fields=None):
    """Receive thumbnails entity data.

    Thumbnail entity can be used to receive binary content of thumbnail based
    on it's content and ThumbnailResolvers.

    Args:
        project_name (str): Name of project where to look for queried entities.
        thumbnail_ids (list[str|ObjectId]): Ids of thumbnail entities.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        cursor: Cursor of queried documents.
    """

    if thumbnail_ids:
        thumbnail_ids = _convert_ids(thumbnail_ids)

    if not thumbnail_ids:
        return []
    query_filter = {
        "type": "thumbnail",
        "_id": {"$in": thumbnail_ids}
    }
    conn = _get_project_connection(project_name)
    return conn.find(query_filter, _prepare_fields(fields))


def get_thumbnail(project_name, thumbnail_id, fields=None):
    """Receive thumbnail entity data.

    Args:
        project_name (str): Name of project where to look for queried entities.
        thumbnail_id (str|ObjectId): Id of thumbnail entity.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        None: If thumbnail with specified id was not found.
        Dict: Thumbnail entity data which can be reduced to specified 'fields'.
    """

    if not thumbnail_id:
        return None
    query_filter = {"type": "thumbnail", "_id": _convert_id(thumbnail_id)}
    conn = _get_project_connection(project_name)
    return conn.find_one(query_filter, _prepare_fields(fields))


def get_workfile_info(
    project_name, asset_id, task_name, filename, fields=None
):
    """Document with workfile information.

    Warning:
        Query is based on filename and context which does not meant it will
        find always right and expected result. Information have limited usage
        and is not recommended to use it as source information about workfile.

    Args:
        project_name (str): Name of project where to look for queried entities.
        asset_id (str|ObjectId): Id of asset entity.
        task_name (str): Task name on asset.
        fields (list[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.
    """

    if not asset_id or not task_name or not filename:
        return None

    query_filter = {
        "type": "workfile",
        "parent": _convert_id(asset_id),
        "task_name": task_name,
        "filename": filename
    }
    conn = _get_project_connection(project_name)
    return conn.find_one(query_filter, _prepare_fields(fields))


"""
## Custom data storage:
- Settings - OP settings overrides and local settings
- Logging - logs from PypeLogger
- Webpublisher - jobs
- Ftrack - events
- Maya - Shaders
    - openpype/hosts/maya/api/shader_definition_editor.py
    - openpype/hosts/maya/plugins/publish/validate_model_name.py

## Global publish plugins
- openpype/plugins/publish/extract_hierarchy_avalon.py
    Create:
    - asset
    Update:
    - asset

## Lib
- openpype/lib/avalon_context.py
    Update:
    - workfile data
- openpype/lib/project_backpack.py
    Update:
    - project
"""
