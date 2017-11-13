import logging

from .vendor import pather
from .vendor.pather.error import ParseError

import avalon.io as io
import avalon.api

log = logging.getLogger(__name__)


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

    if version['name'] == highest_version['name']:
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


def update_context_from_path(path):
    """Update the context using the current scene state.

    When no changes to the context it will not trigger an update.
    When the context for a file could not be parsed an error is logged but not
    raised.

    """
    if not path:
        log.warning("Can't update the current context. Scene is not saved.")
        return

    # Find the current context from the filename
    project = io.find_one({"type": "project"},
                          projection={"config.template.work": True})
    template = project['config']['template']['work']
    # Force to use the registered to root to avoid using wrong paths
    template = pather.format(template, {"root": avalon.api.registered_root()})
    try:
        context = pather.parse(template, path)
    except ParseError:
        log.error("Can't update the current context. Unable to parse the "
                  "context for: %s", path)
        return

    if any([avalon.api.Session['AVALON_ASSET'] != context['asset'],
            avalon.api.Session["AVALON_TASK"] != context['task']]):
        log.info("Updating context to: %s", context)
        avalon.api.update_current_context(context)
