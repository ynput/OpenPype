import os
import sys
import types
import re
import uuid
import json
import collections
import logging
import itertools
import contextlib
import subprocess
import inspect
from abc import ABCMeta, abstractmethod

from avalon import io, pipeline
import six
import avalon.api
from .api import config

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
    pattern = re.compile(r"[\._]v([0-9]+)", re.IGNORECASE)
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

    `$PYPE_SETUP_PATH/repos/pype/path/to/hook.py/HookClass`

    This will load `hook.py`, instantiate HookClass and then execute_hook
    `execute(*args, **kwargs)`

    :param hook: path to hook class
    :type hook: str
    """

    class_name = hook.split("/")[-1]

    abspath = os.path.join(os.getenv('PYPE_SETUP_PATH'),
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


def get_linked_assets(asset_entity):
    """Return linked assets for `asset_entity`."""
    # TODO implement
    return []


def map_subsets_by_family(subsets):
    subsets_by_family = collections.defaultdict(list)
    for subset in subsets:
        family = subset["data"].get("family")
        if not family:
            families = subset["data"].get("families")
            if not families:
                continue
            family = families[0]

        subsets_by_family[family].append(subset)
    return subsets_by_family


class BuildWorkfile:
    """Wrapper for build workfile process.

    Load representations for current context by build presets. Build presets
    are host related, since each host has it's loaders.
    """

    def process(self):
        """Main method of this wrapper.

        Building of workfile is triggered and is possible to implement
        post processing of loaded containers if necessary.
        """
        containers = self.build_workfile()

        return containers

    def build_workfile(self):
        """Prepares and load containers into workfile.

        Loads latest versions of current and linked assets to workfile by logic
        stored in Workfile profiles from presets. Profiles are set by host,
        filtered by current task name and used by families.

        Each family can specify representation names and loaders for
        representations and first available and successful loaded
        representation is returned as container.

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
                raise KeyError(
                    "Duplicated loader name {0}!".format(loader_name)
                )
            loaders_by_name[loader_name] = loader

        # Skip if there are any loaders
        if not loaders_by_name:
            log.warning("There are no registered loaders.")
            return

        # Get current task name
        current_task_name = io.Session["AVALON_TASK"]

        # Load workfile presets for task
        build_presets = self.get_build_presets(current_task_name)

        # Skip if there are any presets for task
        if not build_presets:
            log.warning(
                "Current task `{}` does not have any loading preset.".format(
                    current_task_name
                )
            )
            return

        # Get presets for loading current asset
        current_context_profiles = build_presets.get("current_context")
        # Get presets for loading linked assets
        link_context_profiles = build_presets.get("linked_assets")
        # Skip if both are missing
        if not current_context_profiles and not link_context_profiles:
            log.warning("Current task `{}` has empty loading preset.".format(
                current_task_name
            ))
            return

        elif not current_context_profiles:
            log.warning((
                "Current task `{}` doesn't have any loading"
                " preset for it's context."
            ).format(current_task_name))

        elif not link_context_profiles:
            log.warning((
                "Current task `{}` doesn't have any"
                "loading preset for it's linked assets."
            ).format(current_task_name))

        # Prepare assets to process by workfile presets
        assets = []
        current_asset_id = None
        if current_context_profiles:
            # Add current asset entity if preset has current context set
            assets.append(current_asset_entity)
            current_asset_id = current_asset_entity["_id"]

        if link_context_profiles:
            # Find and append linked assets if preset has set linked mapping
            link_assets = get_linked_assets(current_asset_entity)
            if link_assets:
                assets.extend(link_assets)

        # Skip if there are no assets. This can happen if only linked mapping
        # is set and there are no links for his asset.
        if not assets:
            log.warning(
                "Asset does not have linked assets. Nothing to process."
            )
            return

        # Prepare entities from database for assets
        prepared_entities = self._collect_last_version_repres(assets)

        # Load containers by prepared entities and presets
        loaded_containers = []
        # - Current asset containers
        if current_asset_id and current_asset_id in prepared_entities:
            current_context_data = prepared_entities.pop(current_asset_id)
            loaded_data = self.load_containers_by_asset_data(
                current_context_data, current_context_profiles, loaders_by_name
            )
            if loaded_data:
                loaded_containers.append(loaded_data)

        # - Linked assets container
        for linked_asset_data in prepared_entities.values():
            loaded_data = self.load_containers_by_asset_data(
                linked_asset_data, link_context_profiles, loaders_by_name
            )
            if loaded_data:
                loaded_containers.append(loaded_data)

        # Return list of loaded containers
        return loaded_containers

    def get_build_presets(self, task_name):
        """ Returns presets to build workfile for task name.

        Presets are loaded for current project set in
        io.Session["AVALON_PROJECT"], filtered by registered host
        and entered task name.

        :param task_name: Task name used for filtering build presets.
        :type task_name: str
        :return: preset per eneter task
        :rtype: dict | None
        """
        host_name = avalon.api.registered_host().__name__.rsplit(".", 1)[-1]
        presets = config.get_presets(io.Session["AVALON_PROJECT"])
        # Get presets for host
        build_presets = (
            presets["plugins"]
            .get(host_name, {})
            .get("workfile_build")
        )
        if not build_presets:
            return

        task_name_low = task_name.lower()
        per_task_preset = None
        for preset in build_presets:
            preset_tasks = preset.get("tasks") or []
            preset_tasks_low = [task.lower() for task in preset_tasks]
            if task_name_low in preset_tasks_low:
                per_task_preset = preset
                break

        return per_task_preset

    def _filter_build_profiles(self, build_profiles, loaders_by_name):
        """ Filter build profiles by loaders and prepare process data.

        Valid profile must have "loaders", "families" and "repre_names" keys
        with valid values.
        - "loaders" expects list of strings representing possible loaders.
        - "families" expects list of strings for filtering
                     by main subset family.
        - "repre_names" expects list of strings for filtering by
                        representation name.

        Lowered "families" and "repre_names" are prepared for each profile with
        all required keys.

        :param build_profiles: Profiles for building workfile.
        :type build_profiles: dict
        :param loaders_by_name: Available loaders per name.
        :type loaders_by_name: dict
        :return: Filtered and prepared profiles.
        :rtype: list
        """
        valid_profiles = []
        for profile in build_profiles:
            # Check loaders
            profile_loaders = profile.get("loaders")
            if not profile_loaders:
                log.warning((
                    "Build profile has missing loaders configuration: {0}"
                ).format(json.dumps(profile, indent=4)))
                continue

            # Check if any loader is available
            loaders_match = False
            for loader_name in profile_loaders:
                if loader_name in loaders_by_name:
                    loaders_match = True
                    break

            if not loaders_match:
                log.warning((
                    "All loaders from Build profile are not available: {0}"
                ).format(json.dumps(profile, indent=4)))
                continue

            # Check families
            profile_families = profile.get("families")
            if not profile_families:
                log.warning((
                    "Build profile is missing families configuration: {0}"
                ).format(json.dumps(profile, indent=4)))
                continue

            # Check representation names
            profile_repre_names = profile.get("repre_names")
            if not profile_repre_names:
                log.warning((
                    "Build profile is missing"
                    " representation names filtering: {0}"
                ).format(json.dumps(profile, indent=4)))
                continue

            # Prepare lowered families and representation names
            profile["families_lowered"] = [
                fam.lower() for fam in profile_families
            ]
            profile["repre_names_lowered"] = [
                name.lower() for name in profile_repre_names
            ]

            valid_profiles.append(profile)

        return valid_profiles

    def _prepare_profile_for_subsets(self, subsets, profiles):
        """Select profile for each subset byt it's data.

        Profiles are filtered for each subset individually.
        Profile is filtered by subset's family, optionally by name regex and
        representation names set in profile.
        It is possible to not find matching profile for subset, in that case
        subset is skipped and it is possible that none of subsets have
        matching profile.

        :param subsets: Subset documents.
        :type subsets: list
        :param profiles: Build profiles.
        :type profiles: dict
        :return: Profile by subset's id.
        :rtype: dict
        """
        # Prepare subsets
        subsets_by_family = map_subsets_by_family(subsets)

        profiles_per_subset_id = {}
        for family, subsets in subsets_by_family.items():
            family_low = family.lower()
            for profile in profiles:
                # Skip profile if does not contain family
                if family_low not in profile["families_lowered"]:
                    continue

                # Precompile name filters as regexes
                profile_regexes = profile.get("subset_name_filters")
                if profile_regexes:
                    _profile_regexes = []
                    for regex in profile_regexes:
                        _profile_regexes.append(re.compile(regex))
                    profile_regexes = _profile_regexes

                # TODO prepare regex compilation
                for subset in subsets:
                    # Verify regex filtering (optional)
                    if profile_regexes:
                        valid = False
                        for pattern in profile_regexes:
                            if re.match(pattern, subset["name"]):
                                valid = True
                                break

                        if not valid:
                            continue

                    profiles_per_subset_id[subset["_id"]] = profile

                # break profiles loop on finding the first matching profile
                break
        return profiles_per_subset_id

    def load_containers_by_asset_data(
        self, asset_entity_data, build_profiles, loaders_by_name
    ):
        """Load containers for entered asset entity by Build profiles.

        :param asset_entity_data: Prepared data with subsets, last version
            and representations for specific asset.
        :type asset_entity_data: dict
        :param build_profiles: Build profiles.
        :type build_profiles: dict
        :param loaders_by_name: Available loaders per name.
        :type loaders_by_name: dict
        :return: Output contains asset document and loaded containers.
        :rtype: dict
        """

        # Make sure all data are not empty
        if not asset_entity_data or not build_profiles or not loaders_by_name:
            return

        asset_entity = asset_entity_data["asset_entity"]

        valid_profiles = self._filter_build_profiles(
            build_profiles, loaders_by_name
        )
        if not valid_profiles:
            log.warning(
                "There are not valid Workfile profiles. Skipping process."
            )
            return

        log.debug("Valid Workfile profiles: {}".format(valid_profiles))

        subsets_by_id = {}
        version_by_subset_id = {}
        repres_by_version_id = {}
        for subset_id, in_data in asset_entity_data["subsets"].items():
            subset_entity = in_data["subset_entity"]
            subsets_by_id[subset_entity["_id"]] = subset_entity

            version_data = in_data["version"]
            version_entity = version_data["version_entity"]
            version_by_subset_id[subset_id] = version_entity
            repres_by_version_id[version_entity["_id"]] = (
                version_data["repres"]
            )

        if not subsets_by_id:
            log.warning("There are not subsets for asset {0}".format(
                asset_entity["name"]
            ))
            return

        profiles_per_subset_id = self._prepare_profile_for_subsets(
            subsets_by_id.values(), valid_profiles
        )
        if not profiles_per_subset_id:
            log.warning("There are not valid subsets.")
            return

        valid_repres_by_subset_id = collections.defaultdict(list)
        for subset_id, profile in profiles_per_subset_id.items():
            profile_repre_names = profile["repre_names_lowered"]

            version_entity = version_by_subset_id[subset_id]
            version_id = version_entity["_id"]
            repres = repres_by_version_id[version_id]
            for repre in repres:
                repre_name_low = repre["name"].lower()
                if repre_name_low in profile_repre_names:
                    valid_repres_by_subset_id[subset_id].append(repre)

        # DEBUG message
        msg = "Valid representations for Asset: `{}`".format(
            asset_entity["name"]
        )
        for subset_id, repres in valid_repres_by_subset_id.items():
            subset = subsets_by_id[subset_id]
            msg += "\n# Subset Name/ID: `{}`/{}".format(
                subset["name"], subset_id
            )
            for repre in repres:
                msg += "\n## Repre name: `{}`".format(repre["name"])

        log.debug(msg)

        containers = self._load_containers(
            valid_repres_by_subset_id, subsets_by_id,
            profiles_per_subset_id, loaders_by_name
        )

        return {
            "asset_entity": asset_entity,
            "containers": containers
        }

    def _load_containers(
        self, repres_by_subset_id, subsets_by_id,
        profiles_per_subset_id, loaders_by_name
    ):
        """Real load by collected data happens here.

        Loading of representations per subset happens here. Each subset can
        loads one representation. Loading is tried in specific order.
        Representations are tried to load by names defined in configuration.
        If subset has representation matching representation name each loader
        is tried to load it until any is successful. If none of them was
        successful then next reprensentation name is tried.
        Subset process loop ends when any representation is loaded or
        all matching representations were already tried.

        :param repres_by_subset_id: Available representations mapped
            by their parent (subset) id.
        :type repres_by_subset_id: dict
        :param subsets_by_id: Subset documents mapped by their id.
        :type subsets_by_id: dict
        :param profiles_per_subset_id: Build profiles mapped by subset id.
        :type profiles_per_subset_id: dict
        :param loaders_by_name: Available loaders per name.
        :type loaders_by_name: dict
        :return: Objects of loaded containers.
        :rtype: list
        """
        loaded_containers = []
        for subset_id, repres in repres_by_subset_id.items():
            subset_name = subsets_by_id[subset_id]["name"]

            profile = profiles_per_subset_id[subset_id]
            loaders_last_idx = len(profile["loaders"]) - 1
            repre_names_last_idx = len(profile["repre_names_lowered"]) - 1

            repre_by_low_name = {
                repre["name"].lower(): repre for repre in repres
            }

            is_loaded = False
            for repre_name_idx, profile_repre_name in enumerate(
                profile["repre_names_lowered"]
            ):
                # Break iteration if representation was already loaded
                if is_loaded:
                    break

                repre = repre_by_low_name.get(profile_repre_name)
                if not repre:
                    continue

                for loader_idx, loader_name in enumerate(profile["loaders"]):
                    if is_loaded:
                        break

                    loader = loaders_by_name.get(loader_name)
                    if not loader:
                        continue
                    try:
                        container = avalon.api.load(
                            loader,
                            repre["_id"],
                            name=subset_name
                        )
                        loaded_containers.append(container)
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
                        if loader_idx < loaders_last_idx:
                            msg += " Trying next loader."
                        elif repre_name_idx < repre_names_last_idx:
                            msg += (
                                " Loading of subset `{}` was not successful."
                            ).format(subset_name)
                        else:
                            msg += " Trying next representation."
                        log.info(msg)

        return loaded_containers

    def _collect_last_version_repres(self, asset_entities):
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


def ffprobe_streams(path_to_file):
    """Load streams from entered filepath via ffprobe."""
    log.info(
        "Getting information about input \"{}\".".format(path_to_file)
    )
    args = [
        get_ffmpeg_tool_path("ffprobe"),
        "-v quiet",
        "-print_format json",
        "-show_format",
        "-show_streams",
        "\"{}\"".format(path_to_file)
    ]
    command = " ".join(args)
    log.debug("FFprobe command: \"{}\"".format(command))
    popen = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)

    popen_output = popen.communicate()[0]
    log.debug("FFprobe output: {}".format(popen_output))
    return json.loads(popen_output)["streams"]
