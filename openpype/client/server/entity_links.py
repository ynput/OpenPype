from .utils import get_ayon_server_api_connection
from .entities import get_assets, get_representation_by_id


def get_linked_asset_ids(project_name, asset_doc=None, asset_id=None):
    """Extract linked asset ids from asset document.

    One of asset document or asset id must be passed.

    Note:
        Asset links now works only from asset to assets.

    Args:
        project_name (str): Project where to look for asset.
        asset_doc (dict): Asset document from DB.
        asset_id (str): Asset id to find its document.

    Returns:
        List[Union[ObjectId, str]]: Asset ids of input links.
    """

    output = []
    if not asset_doc and not asset_id:
        return output

    if not asset_id:
        asset_id = asset_doc["_id"]

    con = get_ayon_server_api_connection()
    links = con.get_folder_links(project_name, asset_id, link_direction="in")
    return [
        link["entityId"]
        for link in links
        if link["entityType"] == "folder"
    ]


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

    link_ids = get_linked_asset_ids(project_name, asset_doc, asset_id)
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

    Todos:
        Missing depth query. Not sure how it did find more representations in
            depth, probably links to version?

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

    if not repre_id and not repre_doc:
        return []

    version_id = None
    if repre_doc:
        version_id = repre_doc.get("parent")

    if not version_id:
        repre_doc = get_representation_by_id(
            project_name, repre_id, fields=["parent"]
        )
        if repre_doc:
            version_id = repre_doc["parent"]

    if not version_id:
        return []

    if max_depth is None or max_depth == 0:
        max_depth = 1

    link_types = None
    if link_type:
        link_types = [link_type]

    con = get_ayon_server_api_connection()
    # Store already found version ids to avoid recursion, and also to store
    #   output -> Don't forget to remove 'version_id' at the end!!!
    linked_version_ids = {version_id}
    # Each loop of depth will reset this variable
    versions_to_check = {version_id}
    for _ in range(max_depth):
        if not versions_to_check:
            break

        versions_links = con.get_versions_links(
            project_name,
            versions_to_check,
            link_types=link_types,
            link_direction="out")

        versions_to_check = set()
        for links in versions_links.values():
            for link in links:
                # Care only about version links
                if link["entityType"] != "version":
                    continue
                entity_id = link["entityId"]
                # Skip already found linked version ids
                if entity_id in linked_version_ids:
                    continue
                linked_version_ids.add(entity_id)
                versions_to_check.add(entity_id)

    linked_version_ids.remove(version_id)
    if not linked_version_ids:
        return []
    con = get_ayon_server_api_connection()
    representations = con.get_representations(
        project_name,
        version_ids=linked_version_ids,
        fields=["id"])
    return [
        repre["id"]
        for repre in representations
    ]
