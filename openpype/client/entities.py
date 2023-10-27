from openpype import AYON_SERVER_ENABLED

if not AYON_SERVER_ENABLED:
    from .mongo.entities import *
else:
    from .server.entities import *


def get_asset_name_identifier(asset_doc):
    """Get asset name identifier by asset document.

    This function is added because of AYON implementation where name
        identifier is not just a name but full path.

    Asset document must have "name" key, and "data.parents" when in AYON mode.

    Args:
        asset_doc (dict[str, Any]): Asset document.
    """

    if not AYON_SERVER_ENABLED:
        return asset_doc["name"]
    parents = list(asset_doc["data"]["parents"])
    parents.append(asset_doc["name"])
    return "/" + "/".join(parents)
