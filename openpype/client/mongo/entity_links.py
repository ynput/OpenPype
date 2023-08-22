from .mongo import get_project_connection
from .entities import (
    get_assets,
    get_asset_by_id,
    get_version_by_id,
    get_representation_by_id,
    convert_id,
)


def get_linked_asset_ids(project_name, asset_doc=None, asset_id=None):
    """Extract linked asset ids from asset document.

    One of asset document or asset id must be passed.

    Note:
        Asset links now works only from asset to assets.

    Args:
        asset_doc (dict): Asset document from DB.

    Returns:
        List[Union[ObjectId, str]]: Asset ids of input links.
    """

    output = []
    if not asset_doc and not asset_id:
        return output

    if not asset_doc:
        asset_doc = get_asset_by_id(
            project_name, asset_id, fields=["data.inputLinks"]
        )

    input_links = asset_doc["data"].get("inputLinks")
    if not input_links:
        return output

    for item in input_links:
        # Backwards compatibility for "_id" key which was replaced with
        #   "id"
        if "_id" in item:
            link_id = item["_id"]
        else:
            link_id = item["id"]
        output.append(link_id)
    return output


def get_linked_assets(
    project_name, asset_doc=None, asset_id=None, fields=None
):
    """Return linked assets based on passed asset document.

    One of asset document or asset id must be passed.

    Args:
        project_name (str): Name of project where to look for queried entities.
        asset_doc (Dict[str, Any]): Asset document from database.
        asset_id (Union[ObjectId, str]): Asset id. Can be used instead of
            asset document.
        fields (Iterable[str]): Fields that should be returned. All fields are
            returned if 'None' is passed.

    Returns:
        List[Dict[str, Any]]: Asset documents of input links for passed
            asset doc.
    """

    if not asset_doc:
        if not asset_id:
            return []
        asset_doc = get_asset_by_id(
            project_name,
            asset_id,
            fields=["data.inputLinks"]
        )
        if not asset_doc:
            return []

    link_ids = get_linked_asset_ids(project_name, asset_doc=asset_doc)
    if not link_ids:
        return []

    return list(get_assets(project_name, asset_ids=link_ids, fields=fields))


def get_linked_representation_id(
    project_name, repre_doc=None, repre_id=None, link_type=None, max_depth=None
):
    """Returns list of linked ids of particular type (if provided).

    One of representation document or representation id must be passed.
    Note:
        Representation links now works only from representation through version
            back to representations.

    Args:
        project_name (str): Name of project where look for links.
        repre_doc (Dict[str, Any]): Representation document.
        repre_id (Union[ObjectId, str]): Representation id.
        link_type (str): Type of link (e.g. 'reference', ...).
        max_depth (int): Limit recursion level. Default: 0

    Returns:
        List[ObjectId] Linked representation ids.
    """

    if repre_doc:
        repre_id = repre_doc["_id"]

    if repre_id:
        repre_id = convert_id(repre_id)

    if not repre_id and not repre_doc:
        return []

    version_id = None
    if repre_doc:
        version_id = repre_doc.get("parent")

    if not version_id:
        repre_doc = get_representation_by_id(
            project_name, repre_id, fields=["parent"]
        )
        version_id = repre_doc["parent"]

    if not version_id:
        return []

    version_doc = get_version_by_id(
        project_name, version_id, fields=["type", "version_id"]
    )
    if version_doc["type"] == "hero_version":
        version_id = version_doc["version_id"]

    if max_depth is None:
        max_depth = 0

    match = {
        "_id": version_id,
        # Links are not stored to hero versions at this moment so filter
        #   is limited to just versions
        "type": "version"
    }

    graph_lookup = {
        "from": project_name,
        "startWith": "$data.inputLinks.id",
        "connectFromField": "data.inputLinks.id",
        "connectToField": "_id",
        "as": "outputs_recursive",
        "depthField": "depth"
    }
    if max_depth != 0:
        # We offset by -1 since 0 basically means no recursion
        # but the recursion only happens after the initial lookup
        # for outputs.
        graph_lookup["maxDepth"] = max_depth - 1

    query_pipeline = [
        # Match
        {"$match": match},
        # Recursive graph lookup for inputs
        {"$graphLookup": graph_lookup}
    ]

    conn = get_project_connection(project_name)
    result = conn.aggregate(query_pipeline)
    referenced_version_ids = _process_referenced_pipeline_result(
        result, link_type
    )
    if not referenced_version_ids:
        return []

    ref_ids = conn.distinct(
        "_id",
        filter={
            "parent": {"$in": list(referenced_version_ids)},
            "type": "representation"
        }
    )

    return list(ref_ids)


def _process_referenced_pipeline_result(result, link_type):
    """Filters result from pipeline for particular link_type.

    Pipeline cannot use link_type directly in a query.

    Returns:
        (list)
    """

    referenced_version_ids = set()
    correctly_linked_ids = set()
    for item in result:
        input_links = item.get("data", {}).get("inputLinks")
        if not input_links:
            continue

        _filter_input_links(
            input_links,
            link_type,
            correctly_linked_ids
        )

        # outputs_recursive in random order, sort by depth
        outputs_recursive = item.get("outputs_recursive")
        if not outputs_recursive:
            continue

        for output in sorted(outputs_recursive, key=lambda o: o["depth"]):
            # Leaf
            if output["_id"] not in correctly_linked_ids:
                continue

            _filter_input_links(
                output.get("data", {}).get("inputLinks"),
                link_type,
                correctly_linked_ids
            )

            referenced_version_ids.add(output["_id"])

    return referenced_version_ids


def _filter_input_links(input_links, link_type, correctly_linked_ids):
    if not input_links:  # to handle hero versions
        return

    for input_link in input_links:
        if link_type and input_link["type"] != link_type:
            continue

        link_id = input_link.get("id") or input_link.get("_id")
        if link_id is not None:
            correctly_linked_ids.add(link_id)
