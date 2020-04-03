import os
import sys
import types
import re
import uuid
import json
import getpass
import collections
import logging
import itertools
import contextlib
import subprocess
import inspect
from abc import ABCMeta, abstractmethod
import platform

from avalon import io, pipeline
import six
import avalon.api
from pypeapp import config

log = logging.getLogger(__name__)


def get_paths_from_environ(env_key, return_first=False):
    """Return existing paths from specific envirnment variable.

    :param env_key: Environment key where should look for paths.
    :type env_key: str
    :param return_first: Return first path on `True`, list of all on `False`.
    :type return_first: boolean

    Difference when none of paths exists:
    - when `return_first` is set to `False` then function returns empty list.
    - when `return_first` is set to `True` then function returns `None`.
    """

    existing_paths = []
    paths = os.environ.get(env_key) or ""
    path_items = paths.split(os.pathsep)
    for path in path_items:
        # Skip empty string
        if not path:
            continue
        # Normalize path
        path = os.path.normpath(path)
        # Check if path exists
        if os.path.exists(path):
            # Return path if `return_first` is set to True
            if return_first:
                return path
            # Store path
            existing_paths.append(path)

    # Return None if none of paths exists
    if return_first:
        return None
    # Return all existing paths from environment variable
    return existing_paths


def get_ffmpeg_tool_path(tool="ffmpeg"):
    """Find path to ffmpeg tool in FFMPEG_PATH paths.

    Function looks for tool in paths set in FFMPEG_PATH environment. If tool
    exists then returns it's full path.

    Returns tool name itself when tool path was not found. (FFmpeg path may be
    set in PATH environment variable)
    """

    dir_paths = get_paths_from_environ("FFMPEG_PATH")
    for dir_path in dir_paths:
        for file_name in os.listdir(dir_path):
            base, ext = os.path.splitext(file_name)
            if base.lower() == tool.lower():
                return os.path.join(dir_path, tool)
    return tool


# Special naming case for subprocess since its a built-in method.
def _subprocess(*args, **kwargs):
    """Convenience method for getting output errors for subprocess."""

    # make sure environment contains only strings
    if not kwargs.get("env"):
        filtered_env = {k: str(v) for k, v in os.environ.items()}
    else:
        filtered_env = {k: str(v) for k, v in kwargs.get("env").items()}

    # set overrides
    kwargs['stdout'] = kwargs.get('stdout', subprocess.PIPE)
    kwargs['stderr'] = kwargs.get('stderr', subprocess.STDOUT)
    kwargs['stdin'] = kwargs.get('stdin', subprocess.PIPE)
    kwargs['env'] = filtered_env

    proc = subprocess.Popen(*args, **kwargs)

    output, error = proc.communicate()

    if output:
        output = output.decode("utf-8")
        output += "\n"
        for line in output.strip().split("\n"):
            log.info(line)

    if error:
        error = error.decode("utf-8")
        error += "\n"
        for line in error.strip().split("\n"):
            log.error(line)

    if proc.returncode != 0:
        raise ValueError("\"{}\" was not successful: {}".format(args, output))
    return output


def get_hierarchy(asset_name=None):
    """
    Obtain asset hierarchy path string from mongo db

    Returns:
        string: asset hierarchy path

    """
    if not asset_name:
        asset_name = io.Session.get("AVALON_ASSET", os.environ["AVALON_ASSET"])

    asset_entity = io.find_one({
        "type": 'asset',
        "name": asset_name
    })

    not_set = "PARENTS_NOT_SET"
    entity_parents = asset_entity.get("data", {}).get("parents", not_set)

    # If entity already have parents then just return joined
    if entity_parents != not_set:
        return "/".join(entity_parents)

    # Else query parents through visualParents and store result to entity
    hierarchy_items = []
    entity = asset_entity
    while True:
        parent_id = entity.get("data", {}).get("visualParent")
        if not parent_id:
            break
        entity = io.find_one({"_id": parent_id})
        hierarchy_items.append(entity["name"])

    # Add parents to entity data for next query
    entity_data = asset_entity.get("data", {})
    entity_data["parents"] = hierarchy_items
    io.update_many(
        {"_id": asset_entity["_id"]},
        {"$set": {"data": entity_data}}
    )

    return "/".join(hierarchy_items)


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
    :param update: Dictionary of environment variables
                   and values to add/update.
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
    if version["type"] == "master_version":
        return True

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

        representation_doc = io.find_one(
            {
                "_id": io.ObjectId(representation),
                "type": "representation"
            },
            projection={"parent": True}
        )
        if representation_doc and not is_latest(representation_doc):
            return True
        elif not representation_doc:
            log.debug("Container '{objectName}' has an invalid "
                      "representation, it is missing in the "
                      "database".format(**container))

        checked.add(representation)
    return False


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

    regex = r"[._]v\d+"
    matches = re.findall(regex, str(basename), re.IGNORECASE)
    if not matches:
        log.info("Creating version...")
        new_label = "_v{version:03d}".format(version=1)
        new_basename = "{}{}".format(basename, new_label)
    else:
        label = matches[-1]
        version = re.search(r"\d+", label).group()
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
    asset = io.find_one({
        "name": asset_name,
        "type": "asset"
    })
    assert asset, ("Could not find asset in the database with the name "
                   "'%s'" % asset_name)

    subset = io.find_one({
        "name": subset_name,
        "type": "subset",
        "parent": asset["_id"]
    })
    assert subset, ("Could not find subset in the database with the name "
                    "'%s'" % subset_name)

    version = io.find_one(
        {
            "type": "version",
            "parent": subset["_id"]
        },
        sort=[('name', -1)]
    )

    assert version, "Could not find a version for {}.{}".format(
        asset_name, subset_name
    )

    representation = io.find_one({
        "name": representation_name,
        "type": "representation",
        "parent": version["_id"]}
    )

    assert representation, ("Could not find representation in the database "
                            "with the name '%s'" % representation_name)

    avalon.api.switch(container, representation)

    return representation


def _get_host_name():

    _host = avalon.api.registered_host()
    # This covers nested module name like avalon.maya
    return _host.__name__.rsplit(".", 1)[-1]


def get_asset(asset_name=None):
    """ Returning asset document from database """
    if not asset_name:
        asset_name = avalon.api.Session["AVALON_ASSET"]

    asset_document = io.find_one({
        "name": asset_name,
        "type": "asset"
    })

    if not asset_document:
        raise TypeError("Entity \"{}\" was not found in DB".format(asset_name))

    return asset_document


def get_project():
    io.install()
    return io.find_one({"type": "project"})


def get_version_from_path(file):
    """
    Finds version number in file path string

    Args:
        file (string): file path

    Returns:
        v: version number in string ('001')

    """
    pattern = re.compile(r"[\._]v([0-9]+)")
    try:
        return pattern.findall(file)[0]
    except IndexError:
        log.error(
            "templates:get_version_from_workfile:"
            "`{}` missing version string."
            "Example `v004`".format(file)
        )


def get_avalon_database():
    if io._database is None:
        set_io_database()
    return io._database


def set_io_database():
    required_keys = ["AVALON_PROJECT", "AVALON_ASSET", "AVALON_SILO"]
    for key in required_keys:
        os.environ[key] = os.environ.get(key, "")
    io.install()


def get_all_avalon_projects():
    db = get_avalon_database()
    projects = []
    for name in db.collection_names():
        projects.append(db[name].find_one({'type': 'project'}))
    return projects


def filter_pyblish_plugins(plugins):
    """
    This servers as plugin filter / modifier for pyblish. It will load plugin
    definitions from presets and filter those needed to be excluded.

    :param plugins: Dictionary of plugins produced by :mod:`pyblish-base`
                    `discover()` method.
    :type plugins: Dict
    """
    from pyblish import api

    host = api.current_host()

    presets = config.get_presets().get('plugins', {})

    # iterate over plugins
    for plugin in plugins[:]:
        # skip if there are no presets to process
        if not presets:
            continue

        file = os.path.normpath(inspect.getsourcefile(plugin))
        file = os.path.normpath(file)

        # host determined from path
        host_from_file = file.split(os.path.sep)[-3:-2][0]
        plugin_kind = file.split(os.path.sep)[-2:-1][0]

        try:
            config_data = presets[host]["publish"][plugin.__name__]
        except KeyError:
            try:
                config_data = presets[host_from_file][plugin_kind][plugin.__name__]  # noqa: E501
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


def get_subsets(asset_name,
                regex_filter=None,
                version=None,
                representations=["exr", "dpx"]):
    """
    Query subsets with filter on name.

    The method will return all found subsets and its defined version
    and subsets. Version could be specified with number. Representation
    can be filtered.

    Arguments:
        asset_name (str): asset (shot) name
        regex_filter (raw): raw string with filter pattern
        version (str or int): `last` or number of version
        representations (list): list for all representations

    Returns:
        dict: subsets with version and representaions in keys
    """

    # query asset from db
    asset_io = io.find_one({"type": "asset", "name": asset_name})

    # check if anything returned
    assert asset_io, (
        "Asset not existing. Check correct name: `{}`").format(asset_name)

    # create subsets query filter
    filter_query = {"type": "subset", "parent": asset_io["_id"]}

    # add reggex filter string into query filter
    if regex_filter:
        filter_query.update({"name": {"$regex": r"{}".format(regex_filter)}})
    else:
        filter_query.update({"name": {"$regex": r'.*'}})

    # query all assets
    subsets = [s for s in io.find(filter_query)]

    assert subsets, ("No subsets found. Check correct filter. "
                     "Try this for start `r'.*'`: "
                     "asset: `{}`").format(asset_name)

    output_dict = {}
    # Process subsets
    for subset in subsets:
        if not version:
            version_sel = io.find_one(
                {
                    "type": "version",
                    "parent": subset["_id"]
                },
                sort=[("name", -1)]
            )
        else:
            assert isinstance(version, int), "version needs to be `int` type"
            version_sel = io.find_one({
                "type": "version",
                "parent": subset["_id"],
                "name": int(version)
            })

        find_dict = {"type": "representation",
                     "parent": version_sel["_id"]}

        filter_repr = {"name": {"$in": representations}}

        find_dict.update(filter_repr)
        repres_out = [i for i in io.find(find_dict)]

        if len(repres_out) > 0:
            output_dict[subset["name"]] = {"version": version_sel,
                                           "representaions": repres_out}

    return output_dict


class CustomNone:
    """Created object can be used as custom None (not equal to None).

    WARNING: Multiple created objects are not equal either.
    Exmple:
        >>> a = CustomNone()
        >>> a == None
        False
        >>> b = CustomNone()
        >>> a == b
        False
        >>> a == a
        True
    """

    def __init__(self):
        """Create uuid as identifier for custom None."""
        self.identifier = str(uuid.uuid4())

    def __bool__(self):
        """Return False (like default None)."""
        return False

    def __eq__(self, other):
        """Equality is compared by identifier value."""
        if type(other) == type(self):
            if other.identifier == self.identifier:
                return True
        return False

    def __str__(self):
        """Return value of identifier when converted to string."""
        return self.identifier

    def __repr__(self):
        """Representation of custom None."""
        return "<CustomNone-{}>".format(str(self.identifier))


def execute_hook(hook, *args, **kwargs):
    """
    This will load hook file, instantiate class and call `execute` method
    on it. Hook must be in a form:

    `$PYPE_ROOT/repos/pype/path/to/hook.py/HookClass`

    This will load `hook.py`, instantiate HookClass and then execute_hook
    `execute(*args, **kwargs)`

    :param hook: path to hook class
    :type hook: str
    """

    class_name = hook.split("/")[-1]

    abspath = os.path.join(os.getenv('PYPE_ROOT'),
                           'repos', 'pype', *hook.split("/")[:-1])

    mod_name, mod_ext = os.path.splitext(os.path.basename(abspath))

    if not mod_ext == ".py":
        return False

    module = types.ModuleType(mod_name)
    module.__file__ = abspath

    try:
        with open(abspath) as f:
            six.exec_(f.read(), module.__dict__)

        sys.modules[abspath] = module

    except Exception as exp:
        log.exception("loading hook failed: {}".format(exp),
                      exc_info=True)
        return False

    obj = getattr(module, class_name)
    hook_obj = obj()
    ret_val = hook_obj.execute(*args, **kwargs)
    return ret_val


@six.add_metaclass(ABCMeta)
class PypeHook:

    def __init__(self):
        pass

    @abstractmethod
    def execute(self, *args, **kwargs):
        pass


def get_workfile_build_preset(task_name):
    """ Returns preset variant to build workfile for task name.

    Presets are loaded for current project set in io.Session["AVALON_PROJECT"],
    filtered by registered host and entered task name.

    :param task_name: Task name used for filtering build presets.
    :type task_name: str
    :return: preset per eneter task
    :rtype: dict | None
    """
    host_name = avalon.api.registered_host().__name__.rsplit(".", 1)[-1]
    presets = config.get_presets(io.Session["AVALON_PROJECT"])
    # Get presets for host
    workfile_presets = presets["plugins"].get(host_name, {}).get(
        "workfile_build"
    )
    if not workfile_presets:
        return

    task_name_low = task_name.lower()
    per_task_preset = None
    for variant in workfile_presets:
        variant_tasks = variant.get("tasks")
        if not variant_tasks:
            continue

        variant_tasks_low = [task.lower() for task in variant_tasks]
        if task_name_low not in variant_tasks_low:
            continue

        per_task_preset = variant
        break

    return per_task_preset


def load_containers_by_asset_data(
    asset_entity_data, workfile_preset, loaders_by_name
):
    if not asset_entity_data or not workfile_preset or not loaders_by_name:
        return

    asset_entity = asset_entity_data["asset_entity"]
    # Filter workfile presets by available loaders
    valid_variants = []
    for variant in workfile_preset:
        variant_loaders = variant.get("loaders")
        if not variant_loaders:
            log.warning((
                "Workfile variant has missing loaders configuration: {0}"
            ).format(json.dumps(variant, indent=4)))
            continue

        valid_variant = None
        for loader_name in variant_loaders:
            if loader_name in loaders_by_name:
                valid_variant = variant
                break

        if valid_variant:
            valid_variants.append(valid_variant)
        else:
            log.warning(
                "Loaders in Workfile variant are not available: {0}".format(
                    json.dumps(variant, indent=4)
                )
            )

    if not valid_variants:
        log.warning("There are not valid Workfile variants. Skipping process.")
        return

    log.debug("Valid Workfile variants: {}".format(valid_variants))

    subsets = []
    version_by_subset_id = {}
    repres_by_version_id = {}
    for subset_id, in_data in asset_entity_data["subsets"].items():
        subsets.append(in_data["subset_entity"])
        version_data = in_data["version"]
        version_entity = version_data["version_entity"]
        version_by_subset_id[subset_id] = version_entity
        repres_by_version_id[version_entity["_id"]] = version_data["repres"]

    if not subsets:
        log.warning("There are not subsets for asset {0}".format(
            asset_entity["name"]
        ))
        return

    subsets_by_family = collections.defaultdict(list)
    for subset in subsets:
        family = subset["data"].get("family")
        if not family:
            families = subset["data"].get("families")
            if not families:
                continue
            family = families[0]

        subsets_by_family[family].append(subset)

    valid_subsets_by_id = {}
    variants_per_subset_id = {}
    for family, subsets in subsets_by_family.items():
        family_low = family.lower()
        for variant in valid_variants:
            # Family filtering
            variant_families = variant.get("families") or []
            if not variant_families:
                continue

            variant_families_low = [fam.lower() for fam in variant_families]
            if family_low not in variant_families_low:
                continue

            # Regex filtering (optional)
            variant_regexes = variant.get("subset_name_filters")
            for subset in subsets:
                if variant_regexes:
                    valid = False
                    for pattern in variant_regexes:
                        if re.match(pattern, subset["name"]):
                            valid = True
                            break

                    if not valid:
                        continue

                subset_id = subset["_id"]
                valid_subsets_by_id[subset_id] = subset
                variants_per_subset_id[subset_id] = variant

            # break variants loop on finding the first matching variant
            break

    if not valid_subsets_by_id:
        log.warning("There are not valid subsets.")
        return

    log.debug("Valid subsets: {}".format(valid_subsets_by_id.values()))

    valid_repres_by_subset_id = collections.defaultdict(list)
    for subset_id, _subset_entity in valid_subsets_by_id.items():
        variant = variants_per_subset_id[subset_id]
        variant_repre_names = variant.get("repre_names")
        if not variant_repre_names:
            continue

        # Lower names
        variant_repre_names = [name.lower() for name in variant_repre_names]

        version_entity = version_by_subset_id[subset_id]
        version_id = version_entity["_id"]
        repres = repres_by_version_id[version_id]
        for repre in repres:
            repre_name_low = repre["name"].lower()
            if repre_name_low in variant_repre_names:
                valid_repres_by_subset_id[subset_id].append(repre)

    # DEBUG message
    msg = "Valid representations for Asset: `{}`".format(asset_entity["name"])
    for subset_id, repres in valid_repres_by_subset_id.items():
        subset = valid_subsets_by_id[subset_id]
        msg += "\n# Subset Name/ID: `{}`/{}".format(subset["name"], subset_id)
        for repre in repres:
            msg += "\n## Repre name: `{}`".format(repre["name"])

    log.debug(msg)

    loaded_containers = {
        "asset_entity": asset_entity,
        "containers": []
    }

    for subset_id, repres in valid_repres_by_subset_id.items():
        subset = valid_subsets_by_id[subset_id]
        subset_name = subset["name"]

        variant = variants_per_subset_id[subset_id]

        variant_loader_names = variant["loaders"]
        variant_loader_count = len(variant_loader_names)

        variant_repre_names = variant["repre_names"]
        variant_repre_count = len(variant_repre_names)

        is_loaded = False
        for repre_name_idx, variant_repre_name in enumerate(
                variant_repre_names
        ):
            found_repre = None
            for repre in repres:
                repre_name = repre["name"]
                if repre_name == variant_repre_name:
                    found_repre = repre
                    break

            if not found_repre:
                continue

            for loader_idx, loader_name in enumerate(variant_loader_names):
                if is_loaded:
                    break

                loader = loaders_by_name.get(loader_name)
                if not loader:
                    continue
                try:
                    container = avalon.api.load(
                        loader,
                        found_repre["_id"],
                        name=subset_name
                    )
                    loaded_containers["containers"].append(container)
                    is_loaded = True

                except Exception as exc:
                    if exc == pipeline.IncompatibleLoaderError:
                        log.info((
                            "Loader `{}` is not compatible with"
                            " representation `{}`"
                        ).format(loader_name, repre["name"]))

                    else:
                        log.error(
                            "Unexpected error happened during loading",
                            exc_info=True
                        )

                    msg = "Loading failed."
                    if loader_idx < (variant_loader_count - 1):
                        msg += " Trying next loader."
                    elif repre_name_idx < (variant_repre_count - 1):
                        msg += (
                            " Loading of subset `{}` was not successful."
                        ).format(subset_name)
                    else:
                        msg += " Trying next representation."
                    log.info(msg)

            if is_loaded:
                break

    return loaded_containers


def get_linked_assets(asset_entity):
    """Return linked assets for `asset_entity`."""
    # TODO implement
    return []


def collect_last_version_repres(asset_entities):
    """Collect subsets, versions and representations for asset_entities.

    :param asset_entities: Asset entities for which want to find data
    :type asset_entities: list
    :return: collected entities
    :rtype: dict

    Example output:
    ```
    {
        {Asset ID}: {
            "asset_entity": <AssetEntity>,
            "subsets": {
                {Subset ID}: {
                    "subset_entity": <SubsetEntity>,
                    "version": {
                        "version_entity": <VersionEntity>,
                        "repres": [
                            <RepreEntity1>, <RepreEntity2>, ...
                        ]
                    }
                },
                ...
            }
        },
        ...
    }
    output[asset_id]["subsets"][subset_id]["version"]["repres"]
    ```
    """

    if not asset_entities:
        return {}

    asset_entity_by_ids = {asset["_id"]: asset for asset in asset_entities}

    subsets = list(io.find({
        "type": "subset",
        "parent": {"$in": asset_entity_by_ids.keys()}
    }))
    subset_entity_by_ids = {subset["_id"]: subset for subset in subsets}

    sorted_versions = list(io.find({
        "type": "version",
        "parent": {"$in": subset_entity_by_ids.keys()}
    }).sort("name", -1))

    subset_id_with_latest_version = []
    last_versions_by_id = {}
    for version in sorted_versions:
        subset_id = version["parent"]
        if subset_id in subset_id_with_latest_version:
            continue
        subset_id_with_latest_version.append(subset_id)
        last_versions_by_id[version["_id"]] = version

    repres = io.find({
        "type": "representation",
        "parent": {"$in": last_versions_by_id.keys()}
    })

    output = {}
    for repre in repres:
        version_id = repre["parent"]
        version = last_versions_by_id[version_id]

        subset_id = version["parent"]
        subset = subset_entity_by_ids[subset_id]

        asset_id = subset["parent"]
        asset = asset_entity_by_ids[asset_id]

        if asset_id not in output:
            output[asset_id] = {
                "asset_entity": asset,
                "subsets": {}
            }

        if subset_id not in output[asset_id]["subsets"]:
            output[asset_id]["subsets"][subset_id] = {
                "subset_entity": subset,
                "version": {
                    "version_entity": version,
                    "repres": []
                }
            }

        output[asset_id]["subsets"][subset_id]["version"]["repres"].append(
            repre
        )

    return output


def load_containers_to_workfile():
    """Load containers for (first) workfile.

    Loads latest versions of current and linked assets to workfile by logic
    stored in Workfile variants from presets. Variants are set by host,
    filtered by current task name and used by families.

    Each family can specify representation names and loaders for
    representations and first available and successful loaded representation is
    returned as container.

    At the end you'll get list of loaded containers per each asset.

    loaded_containers [{
        "asset_entity": <AssetEntity1>,
        "containers": [<Container1>, <Container2>, ...]
    }, {
        "asset_entity": <AssetEntity2>,
        "containers": [<Container3>, ...]
    }, {
        ...
    }]
    """
    # Get current asset name and entity
    current_asset_name = io.Session["AVALON_ASSET"]
    current_asset_entity = io.find_one({
        "type": "asset",
        "name": current_asset_name
    })

    # Skip if asset was not found
    if not current_asset_entity:
        print("Asset entity with name `{}` was not found".format(
            current_asset_name
        ))
        return

    # Prepare available loaders
    loaders_by_name = {}
    for loader in avalon.api.discover(avalon.api.Loader):
        loader_name = loader.__name__
        if loader_name in loaders_by_name:
            raise KeyError("Duplicated loader name {0}!".format(loader_name))
        loaders_by_name[loader_name] = loader

    # Skip if there are any loaders
    if not loaders_by_name:
        print("There are no registered loaders.")
        return

    # Get current task name
    current_task_name = io.Session["AVALON_TASK"]
    current_task_name_low = current_task_name.lower()
    # Load workfile presets for task
    workfile_preset = get_workfile_build_preset(current_task_name_low)

    # Skip if there are any presets for task
    if not workfile_preset:
        log.warning(
            "Current task `{}` does not have any loading preset.".format(
                current_task_name
            )
        )
        return

    # Get presets for loading current asset
    current_context = workfile_preset.get("current_context")
    # Get presets for loading linked assets
    link_context = workfile_preset.get("linked_assets")
    # Skip if both are missing
    if not current_context and not link_context:
        log.warning("Current task `{}` has empty loading preset.".format(
            current_task_name
        ))
        return

    elif not current_context:
        log.warning((
            "Current task `{}` doesn't have any loading preset for it's context."
        ).format(current_task_name))

    elif not link_context:
        log.warning((
            "Current task `{}` doesn't have any"
            "loading preset for it's linked assets."
        ).format(current_task_name))

    # Prepare assets to process by workfile presets
    assets = []
    current_asset_id = None
    if current_context:
        # Add current asset entity if preset has current context set
        assets.append(current_asset_entity)
        current_asset_id = current_asset_entity["_id"]

    if link_context:
        # Find and append linked assets if preset has set linked mapping
        link_assets = get_linked_assets(current_asset_entity)
        if link_assets:
            assets.extend(link_assets)

    # Skip if there are any assets
    # - this may happend if only linked mapping is set and there are not links
    if not assets:
        log.warning("Asset does not have linked assets. Nothing to process.")
        return

    # Prepare entities from database for assets
    prepared_entities = collect_last_version_repres(assets)

    # Load containers by prepared entities and presets
    loaded_containers = []
    # - Current asset containers
    if current_asset_id and current_asset_id in prepared_entities:
        current_context_data = prepared_entities.pop(current_asset_id)
        loaded_data = load_containers_by_asset_data(
            current_context_data, current_context, loaders_by_name
        )
        if loaded_data:
            loaded_containers.append(loaded_data)

    # - Linked assets container
    for linked_asset_data in prepared_entities.values():
        loaded_data = load_containers_by_asset_data(
            linked_asset_data, link_context, loaders_by_name
        )
        if loaded_data:
            loaded_containers.append(loaded_data)

    # Return list of loaded containers
    return loaded_containers


def get_last_workfile_path(root, template, file_ext):
    template = re.sub("<.*?>", ".*?", template)
    template = re.sub("{version.*}", "([0-9]+)", template)
    template = re.sub("{comment.*?}", ".+?", template)
    # template = pipeline._format_work_template(template)
    template = "^" + template + "$"

    all_file_names = []
    if os.path.exists(root):
        all_file_names = os.listdir(root)

    filtered_file_names = [
        file_name for file_name in all_file_names
        if os.path.splitext(file_name)[1] == file_ext
    ]

    kwargs = {}
    if platform.system() == "Windows":
        kwargs["flags"] = re.IGNORECASE

    version = None
    last_file_name = None
    re_template = re.compile(template)
    for file_name in sorted(filtered_file_names):
        match = re.match(re_template, file_name, **kwargs)
        if not match:
            continue

        file_version = int(match.group(1))
        if file_version >= version:
            last_file_name = file_name
            version = file_version + 1

    last_file_path = None
    if last_file_name:
        last_file_path = os.path.join(root, last_file_name)

    return last_file_path


def create_first_workfile(file_ext=None):
    """Builds first workfile and load containers for it.

    :param file_ext: Work file extension may be specified otherwise first
    extension in host's registered extensions is used.
    :type file_ext: str
    :return: Workfile path and loaded containers by Asset entity
    :rtype: tuple
    """
    # Get host
    host = avalon.api.registered_host()

    # Workfile extension
    if file_ext is None:
        if not host.file_extensions():
            raise AssertionError(
                "Host doesn't have set file extensions. Can't create workfile."
            )
        file_ext = host.file_extensions()[0]

    workfile_root = host.work_root(io.Session)

    # make sure extension has dot
    if not file_ext.startswith("."):
        file_ext = ".{}".format(file_ext)

    # Create new workfile
    project_doc = io.find_one({"type": "project"})
    asset_name = io.Session["AVALON_ASSET"]
    asset_doc = io.find_one({
        "type": "asset",
        "name": asset_name
    })
    if not asset_doc:
        raise AssertionError(
            "Asset with name `{}` was not found.".format(asset_name)
        )

    root = avalon.api.registered_root()
    template = project_doc["config"]["template"]["workfile"]
    file_path = get_last_workfile_path(root, template, file_ext)
    # TODO what should do if already exists?
    # 1.) create new
    # 2.) override
    # 3.) raise exception
    if file_path is not None:
        log.warning("Workfile already exists`{}`.".format(file_path))
        return file_path

    hierarchy = ""
    parents = asset_doc["data"].get("parents")
    if parents:
        hierarchy = "/".join(parents)

    # Use same data as Workfiles tool
    template_data = {
        "root": root,
        "project": {
            "name": project_doc["name"],
            "code": project_doc["data"].get("code")
        },
        "asset": asset_name,
        "task": io.Session["AVALON_TASK"],
        "hierarchy": hierarchy,
        "version": 1,
        "user": getpass.getuser(),
        "ext": file_ext
    }

    # Use same template as in Workfiles Tool
    template_filled = pipeline.format_template_with_optional_keys(
        template_data, template
    )

    # make sure filled template does not have more dots due to extension
    while ".." in template_filled:
        template_filled = template_filled.replace("..", ".")

    workfile_path = os.path.join(workfile_root, template_filled)
    host.save_file(workfile_path)

    return workfile_path


def build_first_workfile(file_ext=None):
    # DEBUG this should probably be host specific
    # Create workfile
    workfile_path = create_first_workfile(file_ext)
    # Load containers
    loaded_containers = load_containers_to_workfile()
    return (workfile_path, loaded_containers)
