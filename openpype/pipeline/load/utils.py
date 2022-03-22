import os
import platform
import copy
import getpass
import logging
import inspect
import numbers

import six

from avalon import io, schema
from avalon.api import Session, registered_root

from openpype.lib import Anatomy

log = logging.getLogger(__name__)


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


class IncompatibleLoaderError(ValueError):
    """Error when Loader is incompatible with a representation."""
    pass


def get_repres_contexts(representation_ids, dbcon=None):
    """Return parenthood context for representation.

    Args:
        representation_ids (list): The representation ids.
        dbcon (AvalonMongoDB): Mongo connection object. `avalon.io` used when
            not entered.

    Returns:
        dict: The full representation context by representation id.
            keys are repre_id, value is dictionary with full:
                                                        asset_doc
                                                        version_doc
                                                        subset_doc
                                                        repre_doc

    """
    if not dbcon:
        dbcon = io

    contexts = {}
    if not representation_ids:
        return contexts

    _representation_ids = []
    for repre_id in representation_ids:
        if isinstance(repre_id, six.string_types):
            repre_id = io.ObjectId(repre_id)
        _representation_ids.append(repre_id)

    repre_docs = dbcon.find({
        "type": "representation",
        "_id": {"$in": _representation_ids}
    })
    repre_docs_by_id = {}
    version_ids = set()
    for repre_doc in repre_docs:
        version_ids.add(repre_doc["parent"])
        repre_docs_by_id[repre_doc["_id"]] = repre_doc

    version_docs = dbcon.find({
        "type": {"$in": ["version", "hero_version"]},
        "_id": {"$in": list(version_ids)}
    })

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
        _version_docs = dbcon.find({
            "type": "version",
            "_id": {"$in": list(versions_for_hero)}
        })
        _version_data_by_id = {
            version_doc["_id"]: version_doc["data"]
            for version_doc in _version_docs
        }

        for hero_version_doc in hero_version_docs:
            hero_version_id = hero_version_doc["_id"]
            version_id = hero_version_doc["version_id"]
            version_data = copy.deepcopy(_version_data_by_id[version_id])
            version_docs_by_id[hero_version_id]["data"] = version_data

    subset_docs = dbcon.find({
        "type": "subset",
        "_id": {"$in": list(subset_ids)}
    })
    subset_docs_by_id = {}
    asset_ids = set()
    for subset_doc in subset_docs:
        subset_docs_by_id[subset_doc["_id"]] = subset_doc
        asset_ids.add(subset_doc["parent"])

    asset_docs = dbcon.find({
        "type": "asset",
        "_id": {"$in": list(asset_ids)}
    })
    asset_docs_by_id = {
        asset_doc["_id"]: asset_doc
        for asset_doc in asset_docs
    }

    project_doc = dbcon.find_one({"type": "project"})

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
        dbcon = io

    contexts = {}
    if not subset_ids:
        return contexts

    _subset_ids = set()
    for subset_id in subset_ids:
        if isinstance(subset_id, six.string_types):
            subset_id = io.ObjectId(subset_id)
        _subset_ids.add(subset_id)

    subset_docs = dbcon.find({
        "type": "subset",
        "_id": {"$in": list(_subset_ids)}
    })
    subset_docs_by_id = {}
    asset_ids = set()
    for subset_doc in subset_docs:
        subset_docs_by_id[subset_doc["_id"]] = subset_doc
        asset_ids.add(subset_doc["parent"])

    asset_docs = dbcon.find({
        "type": "asset",
        "_id": {"$in": list(asset_ids)}
    })
    asset_docs_by_id = {
        asset_doc["_id"]: asset_doc
        for asset_doc in asset_docs
    }

    project_doc = dbcon.find_one({"type": "project"})

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
        representation (str or io.ObjectId or dict): The representation id
            or full representation as returned by the database.

    Returns:
        dict: The full representation context.

    """

    assert representation is not None, "This is a bug"

    if isinstance(representation, (six.string_types, io.ObjectId)):
        representation = io.find_one(
            {"_id": io.ObjectId(str(representation))})

    version, subset, asset, project = io.parenthood(representation)

    assert all([representation, version, subset, asset, project]), (
        "This is a bug"
    )

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

    loader = Loader(repre_context)
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

    loader = Loader(subset_context)
    return loader.load(subset_context, name, namespace, options)


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

    loader = Loader(subset_contexts)
    return loader.load(subset_contexts, name, namespace, options)


def load_container(
    Loader, representation, namespace=None, name=None, options=None, **kwargs
):
    """Use Loader to load a representation.

    Args:
        Loader (Loader): The loader class to trigger.
        representation (str or io.ObjectId or dict): The representation id
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
        raise RuntimeError("Can't remove container. See log for details.")

    loader = Loader(get_representation_context(container["representation"]))
    return loader.remove(container)


def update_container(container, version=-1):
    """Update a container"""

    # Compute the different version from 'representation'
    current_representation = io.find_one({
        "_id": io.ObjectId(container["representation"])
    })

    assert current_representation is not None, "This is a bug"

    current_version, subset, asset, project = io.parenthood(
        current_representation)

    if version == -1:
        new_version = io.find_one({
            "type": "version",
            "parent": subset["_id"]
        }, sort=[("name", -1)])
    else:
        if isinstance(version, HeroVersionType):
            version_query = {
                "parent": subset["_id"],
                "type": "hero_version"
            }
        else:
            version_query = {
                "parent": subset["_id"],
                "type": "version",
                "name": version
            }
        new_version = io.find_one(version_query)

    assert new_version is not None, "This is a bug"

    new_representation = io.find_one({
        "type": "representation",
        "parent": new_version["_id"],
        "name": current_representation["name"]
    })

    assert new_representation is not None, "Representation wasn't found"

    path = get_representation_path(new_representation)
    assert os.path.exists(path), "Path {} doesn't exist".format(path)

    # Run update on the Loader for this container
    Loader = _get_container_loader(container)
    if not Loader:
        raise RuntimeError("Can't update container. See log for details.")

    loader = Loader(get_representation_context(container["representation"]))
    return loader.update(container, new_representation)


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
        raise RuntimeError("Can't switch container. See log for details.")

    if not hasattr(loader_plugin, "switch"):
        # Backwards compatibility (classes without switch support
        # might be better to just have "switch" raise NotImplementedError
        # on the base class of Loader\
        raise RuntimeError("Loader '{}' does not support 'switch'".format(
            loader_plugin.label
        ))

    # Get the new representation to switch to
    new_representation = io.find_one({
        "type": "representation",
        "_id": representation["_id"],
    })

    new_context = get_representation_context(new_representation)
    if not is_compatible_loader(loader_plugin, new_context):
        raise AssertionError("Must be compatible Loader")

    loader = loader_plugin(new_context)

    return loader.switch(container, new_representation)


def get_representation_path_from_context(context):
    """Preparation wrapper using only context as a argument"""
    representation = context['representation']
    project_doc = context.get("project")
    root = None
    session_project = Session.get("AVALON_PROJECT")
    if project_doc and project_doc["name"] != session_project:
        anatomy = Anatomy(project_doc["name"])
        root = anatomy.roots

    return get_representation_path(representation, root)


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

    from openpype.lib import StringTemplate, TemplateUnsolved

    if dbcon is None:
        dbcon = io

    if root is None:
        root = registered_root()

    def path_from_represenation():
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
            version_, subset, asset, project = dbcon.parenthood(representation)
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
            "silo": asset.get("silo"),
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
        path_from_represenation() or
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
    maj_version, _ = schema.get_schema_version(context["subset"]["schema"])
    if maj_version < 3:
        families = context["version"]["data"].get("families", [])
    else:
        families = context["subset"]["data"]["families"]

    representation = context["representation"]
    has_family = (
        "*" in Loader.families or any(
            family in Loader.families for family in families
        )
    )
    representations = Loader.get_representations()
    has_representation = (
        "*" in representations or representation["name"] in representations
    )
    return has_family and has_representation


def loaders_from_repre_context(loaders, repre_context):
    """Return compatible loaders for by representaiton's context."""

    return [
        loader
        for loader in loaders
        if is_compatible_loader(loader, repre_context)
    ]


def loaders_from_representation(loaders, representation):
    """Return all compatible loaders for a representation."""

    context = get_representation_context(representation)
    return loaders_from_repre_context(loaders, context)
