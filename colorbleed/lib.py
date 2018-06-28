import os
import re
import logging
import importlib

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


def switch_item(container,
                asset_name=None,
                subset_name=None,
                representation_name=None):
    """Switch container asset, subset or representation of a container by name.

    It'll always switch to the latest version - of course a different
    approach could be implemented.

    Args:
        container (dict): data of the item to switch with
        asset_name (str): name of the asset
        subset_name (str): name of the subset
        representation_name (str): name of the representation

    Returns:
        dict

    """

    if all(not x for x in [asset_name, subset_name, representation_name]):
        raise ValueError("Must have at least one change provided to switch.")

    # Collect any of current asset, subset and representation if not provided
    # so we can use the original name from those.
    if any(not x for x in [asset_name, subset_name, representation_name]):
        _id = io.ObjectId(container["representation"])
        representation = io.find_one({"type": "representation", "_id": _id})
        version, subset, asset, project = io.parenthood(representation)

        if asset_name is None:
            asset_name = asset["name"]

        if subset_name is None:
            subset_name = subset["name"]

        if representation_name is None:
            representation_name = representation["name"]

    # Find the new one
    asset = io.find_one({"name": asset_name, "type": "asset"})
    assert asset, ("Could not find asset in the database with the name "
                   "'%s'" % asset_name)

    subset = io.find_one({"name": subset_name,
                          "type": "subset",
                          "parent": asset["_id"]})
    assert subset, ("Could not find subset in the database with the name "
                    "'%s'" % subset_name)

    version = io.find_one({"type": "version",
                           "parent": subset["_id"]},
                          sort=[('name', -1)])

    assert version, "Could not find a version for {}.{}".format(
        asset_name, subset_name
    )

    representation = io.find_one({"name": representation_name,
                                  "type": "representation",
                                  "parent": version["_id"]})

    assert representation, ("Could not find representation in the database with"
                            " the name '%s'" % representation_name)

    avalon.api.switch(container, representation)

    return representation


def _get_host_name():

    _host = avalon.api.registered_host()
    # This covers nested module name like avalon.maya
    return _host.__name__.rsplit(".", 1)[-1]


def collect_container_metadata(container):
    """Add additional data based on the current host

    If the host application's lib module does not have a function to inject
    additional data it will return the input container

    Args:
        container (dict): collection if representation data in host

    Returns:
        generator
    """
    # TODO: Improve method of getting the host lib module
    host_name = _get_host_name()
    package_name = "colorbleed.{}.lib".format(host_name)
    hostlib = importlib.import_module(package_name)

    if not hasattr(hostlib, "get_additional_data"):
        print("{} has no function called "
              "get_additional_data".format(package_name))
        return {}

    return hostlib.get_additional_data(container)


def get_project_fps():
    """Returns project's FPS, if not found will return 25 by default

    Returns:
        float
    """

    project_name = io.active_project()
    project = io.find_one({"name": project_name,
                           "type": "project"},
                          projection={"config.fps": True})

    config = project.get("config", None)
    assert config, "This is a bug"

    fps = config.get("fps", 25.0)

    return float(fps)
