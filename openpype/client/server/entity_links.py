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

    return []


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

    return []


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

    return []
