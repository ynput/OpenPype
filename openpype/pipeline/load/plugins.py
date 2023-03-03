import os
import logging

from openpype.settings import get_system_settings, get_project_settings
from openpype.pipeline import (
    schema,
    legacy_io,
)
from openpype.pipeline.plugin_discover import (
    discover,
    register_plugin,
    register_plugin_path,
    deregister_plugin,
    deregister_plugin_path
)
from .utils import get_representation_path_from_context


class LoaderPlugin(list):
    """Load representation into host application

    Arguments:
        context (dict): avalon-core:context-1.0

    .. versionadded:: 4.0
       This class was introduced

    """

    families = []
    representations = []
    extensions = {"*"}
    order = 0
    is_multiple_contexts_compatible = False
    enabled = True

    options = []

    log = logging.getLogger("SubsetLoader")
    log.propagate = True

    def __init__(self, context):
        self.fname = self.filepath_from_context(context)

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        host_name = os.environ.get("AVALON_APP")
        plugin_type = "load"
        plugin_type_settings = (
            project_settings
            .get(host_name, {})
            .get(plugin_type, {})
        )
        global_type_settings = (
            project_settings
            .get("global", {})
            .get(plugin_type, {})
        )
        if not global_type_settings and not plugin_type_settings:
            return

        plugin_name = cls.__name__

        plugin_settings = None
        # Look for plugin settings in host specific settings
        if plugin_name in plugin_type_settings:
            plugin_settings = plugin_type_settings[plugin_name]

        # Look for plugin settings in global settings
        elif plugin_name in global_type_settings:
            plugin_settings = global_type_settings[plugin_name]

        if not plugin_settings:
            return

        print(">>> We have preset for {}".format(plugin_name))
        for option, value in plugin_settings.items():
            if option == "enabled" and value is False:
                print("  - is disabled by preset")
            else:
                print("  - setting `{}`: `{}`".format(option, value))
            setattr(cls, option, value)

    @classmethod
    def has_valid_extension(cls, repre_doc):
        """Has representation document valid extension for loader.

        Args:
            repre_doc (dict[str, Any]): Representation document.

        Returns:
             bool: Representation has valid extension
        """

        if "*" in cls.extensions:
            return True

        # Get representation main file extension from 'context'
        repre_context = repre_doc.get("context") or {}
        ext = repre_context.get("ext")
        if not ext:
            # Legacy way how to get extensions
            path = repre_doc.get("data", {}).get("path")
            if not path:
                cls.log.info(
                    "Representation doesn't have known source of extension"
                    " information."
                )
                return False

            cls.log.debug("Using legacy source of extension from path.")
            ext = os.path.splitext(path)[-1].lstrip(".")

        # If representation does not have extension then can't be valid
        if not ext:
            return False

        valid_extensions_low = {ext.lower() for ext in cls.extensions}
        return ext.lower() in valid_extensions_low

    @classmethod
    def is_compatible_loader(cls, context):
        """Return whether a loader is compatible with a context.

        On override make sure it is overriden as class or static method.

        This checks the version's families and the representation for the given
        loader plugin.

        Args:
            context (dict[str, Any]): Documents of context for which should
                be loader used.

        Returns:
            bool: Is loader compatible for context.
        """

        plugin_repre_names = cls.get_representations()
        plugin_families = cls.families
        if (
            not plugin_repre_names
            or not plugin_families
            or not cls.extensions
        ):
            return False

        repre_doc = context.get("representation")
        if not repre_doc:
            return False

        plugin_repre_names = set(plugin_repre_names)
        if (
            "*" not in plugin_repre_names
            and repre_doc["name"] not in plugin_repre_names
        ):
            return False

        if not cls.has_valid_extension(repre_doc):
            return False

        plugin_families = set(plugin_families)
        if "*" in plugin_families:
            return True

        subset_doc = context["subset"]
        maj_version, _ = schema.get_schema_version(subset_doc["schema"])
        if maj_version < 3:
            families = context["version"]["data"].get("families")
        else:
            families = subset_doc["data"].get("families")
            if families is None:
                family = subset_doc["data"].get("family")
                if family:
                    families = [family]

        if not families:
            return False
        return any(family in plugin_families for family in families)

    @classmethod
    def get_representations(cls):
        return cls.representations

    @classmethod
    def filepath_from_context(cls, context):
        return get_representation_path_from_context(context)

    def load(self, context, name=None, namespace=None, options=None):
        """Load asset via database

        Arguments:
            context (dict): Full parenthood of representation to load
            name (str, optional): Use pre-defined name
            namespace (str, optional): Use pre-defined namespace
            options (dict, optional): Additional settings dictionary

        """
        raise NotImplementedError("Loader.load() must be "
                                  "implemented by subclass")

    def update(self, container, representation):
        """Update `container` to `representation`

        Arguments:
            container (avalon-core:container-1.0): Container to update,
                from `host.ls()`.
            representation (dict): Update the container to this representation.

        """
        raise NotImplementedError("Loader.update() must be "
                                  "implemented by subclass")

    def remove(self, container):
        """Remove a container

        Arguments:
            container (avalon-core:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the container was deleted

        """

        raise NotImplementedError("Loader.remove() must be "
                                  "implemented by subclass")

    @classmethod
    def get_options(cls, contexts):
        """
            Returns static (cls) options or could collect from 'contexts'.

            Args:
                contexts (list): of repre or subset contexts
            Returns:
                (list)
        """
        return cls.options or []


class SubsetLoaderPlugin(LoaderPlugin):
    """Load subset into host application
    Arguments:
        context (dict): avalon-core:context-1.0
        name (str, optional): Use pre-defined name
        namespace (str, optional): Use pre-defined namespace
    """

    def __init__(self, context):
        pass


def discover_loader_plugins(project_name=None):
    from openpype.lib import Logger

    log = Logger.get_logger("LoaderDiscover")
    plugins = discover(LoaderPlugin)
    if not project_name:
        project_name = legacy_io.active_project()
    system_settings = get_system_settings()
    project_settings = get_project_settings(project_name)
    for plugin in plugins:
        try:
            plugin.apply_settings(project_settings, system_settings)
        except Exception:
            log.warning(
                "Failed to apply settings to loader {}".format(
                    plugin.__name__
                ),
                exc_info=True
            )
    return plugins


def register_loader_plugin(plugin):
    return register_plugin(LoaderPlugin, plugin)


def deregister_loader_plugin(plugin):
    deregister_plugin(LoaderPlugin, plugin)


def deregister_loader_plugin_path(path):
    deregister_plugin_path(LoaderPlugin, path)


def register_loader_plugin_path(path):
    return register_plugin_path(LoaderPlugin, path)
