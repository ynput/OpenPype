import os
import platform
import copy
import getpass
import logging
import inspect
import collections
import numbers

from openpype.host import ILoadHost
from openpype.client import (
    get_project,
    get_assets,
    get_subsets,
    get_versions,
    get_version_by_id,
    get_last_version_by_subset_id,
    get_hero_version_by_subset_id,
    get_version_by_name,
    get_last_versions,
    get_representations,
    get_representation_by_id,
    get_representation_by_name,
    get_representation_parents
)
from openpype.lib import (
    StringTemplate,
    TemplateUnsolved,
)
from openpype.pipeline import (
    legacy_io,
    Anatomy,
)

log = logging.getLogger(__name__)

ContainersFilterResult = collections.namedtuple(
    "ContainersFilterResult",
    ["latest", "outdated", "not_found", "invalid"]
)


class HeroVersionType(object):
    def __init__(self, version):
        assert isinstance(version, numbers.Integral), (
            "Version is not an integer. \"{}\" {}".format(
                version, str(type(version))
            )
        )
        self.version = version

    def __str__(self):
        return str(self.version)

    def __int__(self):
        return int(self.version)

    def __format__(self, format_spec):
        return self.version.__format__(format_spec)


class LoadError(Exception):
    """Known error that happened during loading.

    A message is shown to user (without traceback). Make sure an artist can
    understand the problem.
    """

    pass


class IncompatibleLoaderError(ValueError):
    """Error when Loader is incompatible with a representation."""
    pass


class InvalidRepresentationContext(ValueError):
    """Representation path can't be received using representation document."""
    pass


class LoaderSwitchNotImplementedError(NotImplementedError):
    """Error when `switch` is used with Loader that has no implementation."""
    pass


class LoaderNotFoundError(RuntimeError):
    """Error when Loader plugin for a loader name is not found."""
    pass


def get_repres_contexts(representation_ids, dbcon=None):
    """Return parenthood context for representation.

    Args:
        representation_ids (list): The representation ids.
        dbcon (AvalonMongoDB): Mongo connection object. `avalon.io` used when
            not entered.

    Returns:
        dict: The full representation context by representation id.
            keys are repre_id, value is dictionary with full documents of
            asset, subset, version and representation.
    """

    if not dbcon:
        dbcon = legacy_io

    if not representation_ids:
        return {}

    project_name = dbcon.active_project()
    repre_docs = get_representations(project_name, representation_ids)

    return get_contexts_for_repre_docs(project_name, repre_docs)


def get_contexts_for_repre_docs(project_name, repre_docs):
    contexts = {}
    if not repre_docs:
        return contexts

    repre_docs_by_id = {}
    version_ids = set()
    for repre_doc in repre_docs:
        version_ids.add(repre_doc["parent"])
        repre_docs_by_id[repre_doc["_id"]] = repre_doc

    version_docs = get_versions(
        project_name, version_ids, hero=True
    )

    version_docs_by_id = {}
    hero_version_docs = []
    versions_for_hero = set()
    subset_ids = set()
    for version_doc in version_docs:
        if version_doc["type"] == "hero_version":
            hero_version_docs.append(version_doc)
            versions_for_hero.add(version_doc["version_id"])
        version_docs_by_id[version_doc["_id"]] = version_doc
        subset_ids.add(version_doc["parent"])

    if versions_for_hero:
        _version_docs = get_versions(project_name, versions_for_hero)
        _version_data_by_id = {
            version_doc["_id"]: version_doc["data"]
            for version_doc in _version_docs
        }

        for hero_version_doc in hero_version_docs:
            hero_version_id = hero_version_doc["_id"]
            version_id = hero_version_doc["version_id"]
            version_data = copy.deepcopy(_version_data_by_id[version_id])
            version_docs_by_id[hero_version_id]["data"] = version_data

    subset_docs = get_subsets(project_name, subset_ids)
    subset_docs_by_id = {}
    asset_ids = set()
    for subset_doc in subset_docs:
        subset_docs_by_id[subset_doc["_id"]] = subset_doc
        asset_ids.add(subset_doc["parent"])

    asset_docs = get_assets(project_name, asset_ids)
    asset_docs_by_id = {
        asset_doc["_id"]: asset_doc
        for asset_doc in asset_docs
    }

    project_doc = get_project(project_name)

    for repre_id, repre_doc in repre_docs_by_id.items():
        version_doc = version_docs_by_id[repre_doc["parent"]]
        subset_doc = subset_docs_by_id[version_doc["parent"]]
        asset_doc = asset_docs_by_id[subset_doc["parent"]]
        context = {
            "project": {
                "name": project_doc["name"],
                "code": project_doc["data"].get("code")
            },
            "asset": asset_doc,
            "subset": subset_doc,
            "version": version_doc,
            "representation": repre_doc,
        }
        contexts[repre_id] = context

    return contexts


def get_subset_contexts(subset_ids, dbcon=None):
    """Return parenthood context for subset.

        Provides context on subset granularity - less detail than
        'get_repre_contexts'.
    Args:
        subset_ids (list): The subset ids.
        dbcon (AvalonMongoDB): Mongo connection object. `avalon.io` used when
            not entered.
    Returns:
        dict: The full representation context by representation id.
    """
    if not dbcon:
        dbcon = legacy_io

    contexts = {}
    if not subset_ids:
        return contexts

    project_name = dbcon.active_project()
    subset_docs = get_subsets(project_name, subset_ids)
    subset_docs_by_id = {}
    asset_ids = set()
    for subset_doc in subset_docs:
        subset_docs_by_id[subset_doc["_id"]] = subset_doc
        asset_ids.add(subset_doc["parent"])

    asset_docs = get_assets(project_name, asset_ids)
    asset_docs_by_id = {
        asset_doc["_id"]: asset_doc
        for asset_doc in asset_docs
    }

    project_doc = get_project(project_name)

    for subset_id, subset_doc in subset_docs_by_id.items():
        asset_doc = asset_docs_by_id[subset_doc["parent"]]
        context = {
            "project": {
                "name": project_doc["name"],
                "code": project_doc["data"].get("code")
            },
            "asset": asset_doc,
            "subset": subset_doc
        }
        contexts[subset_id] = context

    return contexts


def get_representation_context(representation):
    """Return parenthood context for representation.

    Args:
        representation (str or ObjectId or dict): The representation id
            or full representation as returned by the database.

    Returns:
        dict: The full representation context.
    """

    assert representation is not None, "This is a bug"

    project_name = legacy_io.active_project()
    if not isinstance(representation, dict):
        representation = get_representation_by_id(
            project_name, representation
        )

    if not representation:
        raise AssertionError("Representation was not found in database")

    version, subset, asset, project = get_representation_parents(
        project_name, representation
    )
    if not version:
        raise AssertionError("Version was not found in database")
    if not subset:
        raise AssertionError("Subset was not found in database")
    if not asset:
        raise AssertionError("Asset was not found in database")
    if not project:
        raise AssertionError("Project was not found in database")

    context = {
        "project": {
            "name": project["name"],
            "code": project["data"].get("code", '')
        },
        "asset": asset,
        "subset": subset,
        "version": version,
        "representation": representation,
    }

    return context


def load_with_repre_context(
    Loader, repre_context, namespace=None, name=None, options=None, **kwargs
):

    # Ensure the Loader is compatible for the representation
    if not is_compatible_loader(Loader, repre_context):
        raise IncompatibleLoaderError(
            "Loader {} is incompatible with {}".format(
                Loader.__name__, repre_context["subset"]["name"]
            )
        )

    # Ensure options is a dictionary when no explicit options provided
    if options is None:
        options = kwargs.get("data", dict())  # "data" for backward compat

    assert isinstance(options, dict), "Options must be a dictionary"

    # Fallback to subset when name is None
    if name is None:
        name = repre_context["subset"]["name"]

    log.info(
        "Running '%s' on '%s'" % (
            Loader.__name__, repre_context["asset"]["name"]
        )
    )

    loader = Loader()

    # Backwards compatibility: Originally the loader's __init__ required the
    # representation context to set `fname` attribute to the filename to load
    # Deprecated - to be removed in OpenPype 3.16.6 or 3.17.0.
    loader._fname = get_representation_path_from_context(repre_context)

    return loader.load(repre_context, name, namespace, options)


def load_with_subset_context(
    Loader, subset_context, namespace=None, name=None, options=None, **kwargs
):

    # Ensure options is a dictionary when no explicit options provided
    if options is None:
        options = kwargs.get("data", dict())  # "data" for backward compat

    assert isinstance(options, dict), "Options must be a dictionary"

    # Fallback to subset when name is None
    if name is None:
        name = subset_context["subset"]["name"]

    log.info(
        "Running '%s' on '%s'" % (
            Loader.__name__, subset_context["asset"]["name"]
        )
    )

    return Loader().load(subset_context, name, namespace, options)


def load_with_subset_contexts(
    Loader, subset_contexts, namespace=None, name=None, options=None, **kwargs
):

    # Ensure options is a dictionary when no explicit options provided
    if options is None:
        options = kwargs.get("data", dict())  # "data" for backward compat

    assert isinstance(options, dict), "Options must be a dictionary"

    # Fallback to subset when name is None
    joined_subset_names = " | ".join(
        context["subset"]["name"]
        for context in subset_contexts
    )
    if name is None:
        name = joined_subset_names

    log.info(
        "Running '{}' on '{}'".format(Loader.__name__, joined_subset_names)
    )

    return Loader().load(subset_contexts, name, namespace, options)


def load_container(
    Loader, representation, namespace=None, name=None, options=None, **kwargs
):
    """Use Loader to load a representation.

    Args:
        Loader (Loader): The loader class to trigger.
        representation (str or ObjectId or dict): The representation id
            or full representation as returned by the database.
        namespace (str, Optional): The namespace to assign. Defaults to None.
        name (str, Optional): The name to assign. Defaults to subset name.
        options (dict, Optional): Additional options to pass on to the loader.

    Returns:
        The return of the `loader.load()` method.

    Raises:
        IncompatibleLoaderError: When the loader is not compatible with
            the representation.

    """

    context = get_representation_context(representation)
    return load_with_repre_context(
        Loader,
        context,
        namespace=namespace,
        name=name,
        options=options,
        **kwargs
    )


def get_loader_identifier(loader):
    """Loader identifier from loader plugin or object.

    Identifier should be stored to container for future management.
    """
    if not inspect.isclass(loader):
        loader = loader.__class__
    return loader.__name__


def get_loaders_by_name():
    from .plugins import discover_loader_plugins

    loaders_by_name = {}
    for loader in discover_loader_plugins():
        loader_name = loader.__name__
        if loader_name in loaders_by_name:
            raise KeyError(
                "Duplicated loader name {} !".format(loader_name)
            )
        loaders_by_name[loader_name] = loader
    return loaders_by_name


def _get_container_loader(container):
    """Return the Loader corresponding to the container"""
    from .plugins import discover_loader_plugins

    loader = container["loader"]
    for Plugin in discover_loader_plugins():
        # TODO: Ensure the loader is valid
        if get_loader_identifier(Plugin) == loader:
            return Plugin
    return None


def remove_container(container):
    """Remove a container"""

    Loader = _get_container_loader(container)
    if not Loader:
        raise LoaderNotFoundError(
            "Can't remove container because loader '{}' was not found."
            .format(container.get("loader"))
        )

    return Loader().remove(container)


def update_container(container, version=-1):
    """Update a container"""

    # Compute the different version from 'representation'
    project_name = legacy_io.active_project()
    current_representation = get_representation_by_id(
        project_name, container["representation"]
    )

    assert current_representation is not None, "This is a bug"

    current_version = get_version_by_id(
        project_name, current_representation["parent"], fields=["parent"]
    )
    if version == -1:
        new_version = get_last_version_by_subset_id(
            project_name, current_version["parent"], fields=["_id"]
        )

    elif isinstance(version, HeroVersionType):
        new_version = get_hero_version_by_subset_id(
            project_name, current_version["parent"], fields=["_id"]
        )

    else:
        new_version = get_version_by_name(
            project_name, version, current_version["parent"], fields=["_id"]
        )

    assert new_version is not None, "This is a bug"

    new_representation = get_representation_by_name(
        project_name, current_representation["name"], new_version["_id"]
    )
    assert new_representation is not None, "Representation wasn't found"

    path = get_representation_path(new_representation)
    assert os.path.exists(path), "Path {} doesn't exist".format(path)

    # Run update on the Loader for this container
    Loader = _get_container_loader(container)
    if not Loader:
        raise LoaderNotFoundError(
            "Can't update container because loader '{}' was not found."
            .format(container.get("loader"))
        )

    return Loader().update(container, new_representation)


def switch_container(container, representation, loader_plugin=None):
    """Switch a container to representation

    Args:
        container (dict): container information
        representation (dict): representation data from document

    Returns:
        function call
    """

    # Get the Loader for this container
    if loader_plugin is None:
        loader_plugin = _get_container_loader(container)

    if not loader_plugin:
        raise LoaderNotFoundError(
            "Can't switch container because loader '{}' was not found."
            .format(container.get("loader"))
        )

    if not hasattr(loader_plugin, "switch"):
        # Backwards compatibility (classes without switch support
        # might be better to just have "switch" raise NotImplementedError
        # on the base class of Loader\
        raise LoaderSwitchNotImplementedError(
            "Loader {} does not support 'switch'".format(loader_plugin.label)
        )

    # Get the new representation to switch to
    project_name = legacy_io.active_project()
    new_representation = get_representation_by_id(
        project_name, representation["_id"]
    )

    new_context = get_representation_context(new_representation)
    if not is_compatible_loader(loader_plugin, new_context):
        raise IncompatibleLoaderError(
            "Loader {} is incompatible with {}".format(
                loader_plugin.__name__, new_context["subset"]["name"]
            )
        )

    loader = loader_plugin(new_context)

    return loader.switch(container, new_representation)


def get_representation_path_from_context(context):
    """Preparation wrapper using only context as a argument"""
    representation = context['representation']
    project_doc = context.get("project")
    root = None
    session_project = legacy_io.Session.get("AVALON_PROJECT")
    if project_doc and project_doc["name"] != session_project:
        anatomy = Anatomy(project_doc["name"])
        root = anatomy.roots

    return get_representation_path(representation, root)


def get_representation_path_with_anatomy(repre_doc, anatomy):
    """Receive representation path using representation document and anatomy.

    Anatomy is used to replace 'root' key in representation file. Ideally
    should be used instead of 'get_representation_path' which is based on
    "current context".

    Future notes:
        We want also be able store resources into representation and I can
        imagine the result should also contain paths to possible resources.

    Args:
        repre_doc (Dict[str, Any]): Representation document.
        anatomy (Anatomy): Project anatomy object.

    Returns:
        Union[None, TemplateResult]: None if path can't be received

    Raises:
        InvalidRepresentationContext: When representation data are probably
            invalid or not available.
    """

    try:
        template = repre_doc["data"]["template"]

    except KeyError:
        raise InvalidRepresentationContext((
            "Representation document does not"
            " contain template in data ('data.template')"
        ))

    try:
        context = repre_doc["context"]
        context["root"] = anatomy.roots
        path = StringTemplate.format_strict_template(template, context)

    except TemplateUnsolved as exc:
        raise InvalidRepresentationContext((
            "Couldn't resolve representation template with available data."
            " Reason: {}".format(str(exc))
        ))

    return path.normalized()


def get_representation_path(representation, root=None, dbcon=None):
    """Get filename from representation document

    There are three ways of getting the path from representation which are
    tried in following sequence until successful.
    1. Get template from representation['data']['template'] and data from
       representation['context']. Then format template with the data.
    2. Get template from project['config'] and format it with default data set
    3. Get representation['data']['path'] and use it directly

    Args:
        representation(dict): representation document from the database

    Returns:
        str: fullpath of the representation

    """

    if dbcon is None:
        dbcon = legacy_io

    if root is None:
        from openpype.pipeline import registered_root

        root = registered_root()

    def path_from_representation():
        try:
            template = representation["data"]["template"]
        except KeyError:
            return None

        try:
            context = representation["context"]
            context["root"] = root
            path = StringTemplate.format_strict_template(
                template, context
            )
            # Force replacing backslashes with forward slashed if not on
            #   windows
            if platform.system().lower() != "windows":
                path = path.replace("\\", "/")
        except (TemplateUnsolved, KeyError):
            # Template references unavailable data
            return None

        if not path:
            return path

        normalized_path = os.path.normpath(path)
        if os.path.exists(normalized_path):
            return normalized_path
        return path

    def path_from_config():
        try:
            project_name = dbcon.active_project()
            version_, subset, asset, project = get_representation_parents(
                project_name, representation
            )
        except ValueError:
            log.debug(
                "Representation %s wasn't found in database, "
                "like a bug" % representation["name"]
            )
            return None

        try:
            template = project["config"]["template"]["publish"]
        except KeyError:
            log.debug(
                "No template in project %s, "
                "likely a bug" % project["name"]
            )
            return None

        # default list() in get would not discover missing parents on asset
        parents = asset.get("data", {}).get("parents")
        if parents is not None:
            hierarchy = "/".join(parents)

        # Cannot fail, required members only
        data = {
            "root": root,
            "project": {
                "name": project["name"],
                "code": project.get("data", {}).get("code")
            },
            "asset": asset["name"],
            "hierarchy": hierarchy,
            "subset": subset["name"],
            "version": version_["name"],
            "representation": representation["name"],
            "family": representation.get("context", {}).get("family"),
            "user": dbcon.Session.get("AVALON_USER", getpass.getuser()),
            "app": dbcon.Session.get("AVALON_APP", ""),
            "task": dbcon.Session.get("AVALON_TASK", "")
        }

        try:
            template_obj = StringTemplate(template)
            path = str(template_obj.format(data))
            # Force replacing backslashes with forward slashed if not on
            #   windows
            if platform.system().lower() != "windows":
                path = path.replace("\\", "/")

        except KeyError as e:
            log.debug("Template references unavailable data: %s" % e)
            return None

        normalized_path = os.path.normpath(path)
        if os.path.exists(normalized_path):
            return normalized_path
        return path

    def path_from_data():
        if "path" not in representation["data"]:
            return None

        path = representation["data"]["path"]
        # Force replacing backslashes with forward slashed if not on
        #   windows
        if platform.system().lower() != "windows":
            path = path.replace("\\", "/")

        if os.path.exists(path):
            return os.path.normpath(path)

        dir_path, file_name = os.path.split(path)
        if not os.path.exists(dir_path):
            return

        base_name, ext = os.path.splitext(file_name)
        file_name_items = None
        if "#" in base_name:
            file_name_items = [part for part in base_name.split("#") if part]
        elif "%" in base_name:
            file_name_items = base_name.split("%")

        if not file_name_items:
            return

        filename_start = file_name_items[0]

        for _file in os.listdir(dir_path):
            if _file.startswith(filename_start) and _file.endswith(ext):
                return os.path.normpath(path)

    return (
        path_from_representation() or
        path_from_config() or
        path_from_data()
    )


def is_compatible_loader(Loader, context):
    """Return whether a loader is compatible with a context.

    This checks the version's families and the representation for the given
    Loader.

    Returns:
        bool
    """

    return Loader.is_compatible_loader(context)


def loaders_from_repre_context(loaders, repre_context):
    """Return compatible loaders for by representaiton's context."""

    return [
        loader
        for loader in loaders
        if is_compatible_loader(loader, repre_context)
    ]


def filter_repre_contexts_by_loader(repre_contexts, loader):
    """Filter representation contexts for loader.

    Args:
        repre_contexts (list[dict[str, Ant]]): Representation context.
        loader (LoaderPlugin): Loader plugin to filter contexts for.

    Returns:
        list[dict[str, Any]]: Filtered representation contexts.
    """

    return [
        repre_context
        for repre_context in repre_contexts
        if is_compatible_loader(loader, repre_context)
    ]


def loaders_from_representation(loaders, representation):
    """Return all compatible loaders for a representation."""

    context = get_representation_context(representation)
    return loaders_from_repre_context(loaders, context)


def any_outdated_containers(host=None, project_name=None):
    """Check if there are any outdated containers in scene."""

    if get_outdated_containers(host, project_name):
        return True
    return False


def get_outdated_containers(host=None, project_name=None):
    """Collect outdated containers from host scene.

    Currently registered host and project in global session are used if
    arguments are not passed.

    Args:
        host (ModuleType): Host implementation with 'ls' function available.
        project_name (str): Name of project in which context we are.
    """

    if host is None:
        from openpype.pipeline import registered_host

        host = registered_host()

    if project_name is None:
        project_name = legacy_io.active_project()

    if isinstance(host, ILoadHost):
        containers = host.get_containers()
    else:
        containers = host.ls()
    return filter_containers(containers, project_name).outdated


def filter_containers(containers, project_name):
    """Filter containers and split them into 4 categories.

    Categories are 'latest', 'outdated', 'invalid' and 'not_found'.
    The 'lastest' containers are from last version, 'outdated' are not,
    'invalid' are invalid containers (invalid content) and 'not_found' has
    some missing entity in database.

    Args:
        containers (Iterable[dict]): List of containers referenced into scene.
        project_name (str): Name of project in which context shoud look for
            versions.

    Returns:
        ContainersFilterResult: Named tuple with 'latest', 'outdated',
            'invalid' and 'not_found' containers.
    """

    # Make sure containers is list that won't change
    containers = list(containers)

    outdated_containers = []
    uptodate_containers = []
    not_found_containers = []
    invalid_containers = []
    output = ContainersFilterResult(
        uptodate_containers,
        outdated_containers,
        not_found_containers,
        invalid_containers
    )
    # Query representation docs to get it's version ids
    repre_ids = {
        container["representation"]
        for container in containers
        if container["representation"]
    }
    if not repre_ids:
        if containers:
            invalid_containers.extend(containers)
        return output

    repre_docs = get_representations(
        project_name,
        representation_ids=repre_ids,
        fields=["_id", "parent"]
    )
    # Store representations by stringified representation id
    repre_docs_by_str_id = {}
    repre_docs_by_version_id = collections.defaultdict(list)
    for repre_doc in repre_docs:
        repre_id = str(repre_doc["_id"])
        version_id = repre_doc["parent"]
        repre_docs_by_str_id[repre_id] = repre_doc
        repre_docs_by_version_id[version_id].append(repre_doc)

    # Query version docs to get it's subset ids
    # - also query hero version to be able identify if representation
    #   belongs to existing version
    version_docs = get_versions(
        project_name,
        version_ids=repre_docs_by_version_id.keys(),
        hero=True,
        fields=["_id", "parent", "type"]
    )
    verisons_by_id = {}
    versions_by_subset_id = collections.defaultdict(list)
    hero_version_ids = set()
    for version_doc in version_docs:
        version_id = version_doc["_id"]
        # Store versions by their ids
        verisons_by_id[version_id] = version_doc
        # There's no need to query subsets for hero versions
        #   - they are considered as latest?
        if version_doc["type"] == "hero_version":
            hero_version_ids.add(version_id)
            continue
        subset_id = version_doc["parent"]
        versions_by_subset_id[subset_id].append(version_doc)

    last_versions = get_last_versions(
        project_name,
        subset_ids=versions_by_subset_id.keys(),
        fields=["_id"]
    )
    # Figure out which versions are outdated
    outdated_version_ids = set()
    for subset_id, last_version_doc in last_versions.items():
        for version_doc in versions_by_subset_id[subset_id]:
            version_id = version_doc["_id"]
            if version_id != last_version_doc["_id"]:
                outdated_version_ids.add(version_id)

    # Based on all collected data figure out which containers are outdated
    #   - log out if there are missing representation or version documents
    for container in containers:
        container_name = container["objectName"]
        repre_id = container["representation"]
        if not repre_id:
            invalid_containers.append(container)
            continue

        repre_doc = repre_docs_by_str_id.get(repre_id)
        if not repre_doc:
            log.debug((
                "Container '{}' has an invalid representation."
                " It is missing in the database."
            ).format(container_name))
            not_found_containers.append(container)
            continue

        version_id = repre_doc["parent"]
        if version_id in outdated_version_ids:
            outdated_containers.append(container)

        elif version_id not in verisons_by_id:
            log.debug((
                "Representation on container '{}' has an invalid version."
                " It is missing in the database."
            ).format(container_name))
            not_found_containers.append(container)

        else:
            uptodate_containers.append(container)

    return output
