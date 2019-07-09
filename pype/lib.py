import os
import re
import logging
import importlib
import itertools
import contextlib

from .vendor import pather
from .vendor.pather.error import ParseError

import avalon.io as io
import avalon.api
import avalon

log = logging.getLogger(__name__)


def get_handle_irregular(asset):
    data = asset["data"]
    handle_start = data.get("handle_start", 0)
    handle_end = data.get("handle_end", 0)
    return (handle_start, handle_end)


def add_tool_to_environment(tools):
    """
    It is adding dynamic environment to os environment.

    Args:
        tool (list, tuple): list of tools, name should corespond to json/toml

    Returns:
        os.environ[KEY]: adding to os.environ
    """

    import acre
    tools_env = acre.get_tools(tools)
    env = acre.compute(tools_env)
    env = acre.merge(env, current_env=dict(os.environ))
    os.environ.update(env)


@contextlib.contextmanager
def modified_environ(*remove, **update):
    """
    Temporarily updates the ``os.environ`` dictionary in-place.

    The ``os.environ`` dictionary is updated in-place so that the modification
    is sure to work in all situations.

    :param remove: Environment variables to remove.
    :param update: Dictionary of environment variables and values to add/update.
    """
    env = os.environ
    update = update or {}
    remove = remove or []

    # List of environment variables being updated or removed.
    stomped = (set(update.keys()) | set(remove)) & set(env.keys())
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        [env.pop(k, None) for k in remove]
        yield
    finally:
        env.update(update_after)
        [env.pop(k) for k in remove_after]


def pairwise(iterable):
    """s -> (s0,s1), (s2,s3), (s4, s5), ..."""
    a = iter(iterable)
    return itertools.izip(a, a)


def grouper(iterable, n, fillvalue=None):
    """Collect data into fixed-length chunks or blocks

    Examples:
        grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx

    """

    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args)


def is_latest(representation):
    """Return whether the representation is from latest version

    Args:
        representation (dict): The representation document from the database.

    Returns:
        bool: Whether the representation is of latest version.

    """

    version = io.find_one({"_id": representation['parent']})

    # Get highest version under the parent
    highest_version = io.find_one({
        "type": "version",
        "parent": version["parent"]
    }, sort=[("name", -1)], projection={"name": True})

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

        representation_doc = io.find_one({"_id": io.ObjectId(representation),
                                          "type": "representation"},
                                         projection={"parent": True})
        if representation_doc and not is_latest(representation_doc):
            return True
        elif not representation_doc:
            log.debug("Container '{objectName}' has an invalid "
                      "representation, it is missing in the "
                      "database".format(**container))

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
        "task": avalon.api.Session["AVALON_TASK"]
        # "app": avalon.api.Session["AVALON_APP"]
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

    if not new_basename.endswith(new_label):
        index = (new_basename.find(new_label))
        index += len(new_label)
        new_basename = new_basename[:index]

    new_filename = "{}{}".format(new_basename, ext)
    new_filename = os.path.join(dirname, new_filename)
    new_filename = os.path.normpath(new_filename)

    if new_filename == filepath:
        raise RuntimeError("Created path is the same as current file,"
                           "this is a bug")

    for file in os.listdir(dirname):
        if file.endswith(ext) and file.startswith(new_basename):
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
    package_name = "pype.{}.lib".format(host_name)
    hostlib = importlib.import_module(package_name)

    if not hasattr(hostlib, "get_additional_data"):
        return {}

    return hostlib.get_additional_data(container)


def get_asset_fps():
    """Returns project's FPS, if not found will return 25 by default

    Returns:
        int, float

    """

    key = "fps"

    # FPS from asset data (if set)
    asset_data = get_asset_data()
    if key in asset_data:
        return asset_data[key]

    # FPS from project data (if set)
    project_data = get_project_data()
    if key in project_data:
        return project_data[key]

    # Fallback to 25 FPS
    return 25.0


def get_project_data():
    """Get the data of the current project

    The data of the project can contain things like:
        resolution
        fps
        renderer

    Returns:
        dict:

    """

    project_name = io.active_project()
    project = io.find_one({"name": project_name,
                           "type": "project"},
                          projection={"data": True})

    data = project.get("data", {})

    return data


def get_asset_data(asset=None):
    """Get the data from the current asset

    Args:
        asset(str, Optional): name of the asset, eg:

    Returns:
        dict
    """
    asset_name = asset or avalon.api.Session["AVALON_ASSET"]
    document = io.find_one({"name": asset_name,
                            "type": "asset"})
    data = document.get("data", {})

    return data


def get_data_hierarchical_attr(entity, attr_name):
    vp_attr = 'visualParent'
    data = entity['data']
    value = data.get(attr_name, None)
    if value is not None:
        return value
    elif vp_attr in data:
        if data[vp_attr] is None:
            parent_id = entity['parent']
        else:
            parent_id = data[vp_attr]
        parent = io.find_one({"_id": parent_id})
        return get_data_hierarchical_attr(parent, attr_name)
    else:
        return None


def get_avalon_project_config_schema():
    schema = 'avalon-core:config-1.0'
    return schema


def get_avalon_project_template_schema():
    schema = "avalon-core:project-2.0"
    return schema


def get_avalon_project_template():
    from pypeapp import Anatomy

    """
    Get avalon template

    Returns:
        dictionary with templates
    """
    templates = Anatomy().templates
    proj_template = {}
    proj_template['workfile'] = templates["avalon"]["workfile"]
    proj_template['work'] = templates["avalon"]["work"]
    proj_template['publish'] = templates["avalon"]["publish"]
    return proj_template


def get_avalon_asset_template_schema():
    schema = "avalon-core:asset-2.0"
    return schema


def get_avalon_database():
    if io._database is None:
        set_io_database()
    return io._database


def set_io_database():
    project = os.environ.get('AVALON_PROJECT', '')
    asset = os.environ.get('AVALON_ASSET', '')
    silo = os.environ.get('AVALON_SILO', '')
    os.environ['AVALON_PROJECT'] = project
    os.environ['AVALON_ASSET'] = asset
    os.environ['AVALON_SILO'] = silo
    io.install()


def get_all_avalon_projects():
    db = get_avalon_database()
    project_names = db.collection_names()
    projects = []
    for name in project_names:
        projects.append(db[name].find_one({'type': 'project'}))
    return projects


def get_presets_path():
    templates = os.environ['PYPE_CONFIG']
    path_items = [templates, 'presets']
    filepath = os.path.sep.join(path_items)
    return filepath


def filter_pyblish_plugins(plugins):
    """
    This servers as plugin filter / modifier for pyblish. It will load plugin
    definitions from presets and filter those needed to be excluded.

    :param plugins: Dictionary of plugins produced by :mod:`pyblish-base`
                    `discover()` method.
    :type plugins: Dict
    """
    from pypeapp import config
    from pyblish import api

    host = api.current_host()

    # iterate over plugins
    for plugin in plugins[:]:
        try:
            config_data = config.get_presets()['plugins'][host]["publish"][plugin.__name__]  # noqa: E501
        except KeyError:
            continue

        for option, value in config_data.items():
            if option == "enabled" and value is False:
                log.info('removing plugin {}'.format(plugin.__name__))
                plugins.remove(plugin)
            else:
                log.info('setting {}:{} on plugin {}'.format(
                    option, value, plugin.__name__))

                setattr(plugin, option, value)
