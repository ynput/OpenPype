import os
import re
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


def update_task_from_path(path):
    """Update the context using the current scene state.

    When no changes to the context it will not trigger an update.
    When the context for a file could not be parsed an error is logged but not
    raised.

    """
    if not path:
        log.warning("Can't update the current task. Scene is not saved.")
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
        log.error("Can't update the current task. Unable to parse the "
                  "task for: %s (pattern: %s)", path, template)
        return

    # Find the changes between current Session and the path's context.
    current = {
        "asset": avalon.api.Session["AVALON_ASSET"],
        "task": avalon.api.Session["AVALON_TASK"],
        "app": avalon.api.Session["AVALON_APP"]
    }
    changes = {key: context[key] for key, current_value in current.items()
               if context[key] != current_value}

    if changes:
        log.info("Updating work task to: %s", context)
        avalon.api.update_current_task(**changes)


def _rreplace(s, a, b, n=1):
    """Replace a with b in string s from right side n times"""
    return b.join(s.rsplit(a, n))


def version_up(filepath):
    """Version up filepath to a new non-existing version.

    Parses for a version identifier like `_v001` or `.v001`
    When no version present _v001 is appended as suffix.

    Returns:
        str: filepath with increased version number

    """

    dirname = os.path.dirname(filepath)
    basename, ext = os.path.splitext(os.path.basename(filepath))

    regex = "[._]v\d+"
    matches = re.findall(regex, str(basename), re.IGNORECASE)
    if not matches:
        log.info("Creating version...")
        new_label = "_v{version:03d}".format(version=1)
        new_basename = "{}{}".format(basename, new_label)
    else:
        label = matches[-1]
        version = re.search("\d+", label).group()
        padding = len(version)

        new_version = int(version) + 1
        new_version = '{version:0{padding}d}'.format(version=new_version,
                                                     padding=padding)
        new_label = label.replace(version, new_version, 1)
        new_basename = _rreplace(basename, label, new_label)

    new_filename = "{}{}".format(new_basename, ext)
    new_filename = os.path.join(dirname, new_filename)
    new_filename = os.path.normpath(new_filename)

    if new_filename == filepath:
        raise RuntimeError("Created path is the same as current file,"
                           "this is a bug")

    if os.path.exists(new_filename):
        log.info("Skipping existing version %s" % new_label)
        return version_up(new_filename)

    log.info("New version %s" % new_label)
    return new_filename
