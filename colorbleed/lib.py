import avalon.io as io
import avalon.api


def is_latest(representation):
    """Return whether the representation is from latest version

    Args:
        representation (str or io.ObjectId): The representation id.

    Returns:
        bool: Whether the representation is of latest version.

    """

    rep = io.find_one({"_id": io.ObjectId(representation),
                       "type": "representation"})
    version = io.find_one({"_id": rep['parent']})

    # Get highest version under the parent
    highest_version = io.find_one({
        "type": "version",
        "parent": version["parent"]
    }, sort=[("name", -1)])

    if version['name'] != highest_version['name']:
        return True
    else:
        return False


def any_outdated():
    """Return whether the current scene has any outdated content"""

    checked = set()
    host = avalon.api.registered_host()
    for container in host.ls():
        representation = container['representation']
        if representation in checked:
            continue

        if not is_latest(container['representation']):
            return True

        checked.add(representation)
    return False