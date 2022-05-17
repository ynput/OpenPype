import os
import inspect
import traceback

from openpype.api import Logger
from openpype.lib.python_module_tools import (
    modules_from_path,
    classes_from_module,
)

log = Logger.get_logger(__name__)


class DiscoverResult:
    """Result of Plug-ins discovery of a single superclass type.

    Stores discovered, duplicated, ignored and abstract plugins and file paths
    which crashed on execution of file.
    """

    def __init__(self, superclass):
        self.superclass = superclass
        self.plugins = []
        self.crashed_file_paths = {}
        self.duplicated_plugins = []
        self.abstract_plugins = []
        self.ignored_plugins = set()
        # Store loaded modules to keep them in memory
        self._modules = set()

    def __iter__(self):
        for plugin in self.plugins:
            yield plugin

    def __getitem__(self, item):
        return self.plugins[item]

    def __setitem__(self, item, value):
        self.plugins[item] = value

    def add_module(self, module):
        """Add dynamically loaded python module to keep it in memory."""
        self._modules.add(module)

    def get_report(self, only_errors=True, exc_info=True, full_report=False):
        lines = []
        if not only_errors:
            # Successfully discovered plugins
            if self.plugins or full_report:
                lines.append(
                    "*** Discovered {} plugins".format(len(self.plugins))
                )
                for cls in self.plugins:
                    lines.append("- {}".format(cls.__class__.__name__))

            # Plugin that were defined to be ignored
            if self.ignored_plugins or full_report:
                lines.append("*** Ignored plugins {}".format(len(
                    self.ignored_plugins
                )))
                for cls in self.ignored_plugins:
                    lines.append("- {}".format(cls.__name__))

        # Abstract classes
        if self.abstract_plugins or full_report:
            lines.append("*** Discovered {} abstract plugins".format(len(
                self.abstract_plugins
            )))
            for cls in self.abstract_plugins:
                lines.append("- {}".format(cls.__name__))

        # Abstract classes
        if self.duplicated_plugins or full_report:
            lines.append("*** There were {} duplicated plugins".format(len(
                self.duplicated_plugins
            )))
            for cls in self.duplicated_plugins:
                lines.append("- {}".format(cls.__name__))

        if self.crashed_file_paths or full_report:
            lines.append("*** Failed to load {} files".format(len(
                self.crashed_file_paths
            )))
            for path, exc_info_args in self.crashed_file_paths.items():
                lines.append("- {}".format(path))
                if exc_info:
                    lines.append(10 * "*")
                    lines.extend(traceback.format_exception(*exc_info_args))
                    lines.append(10 * "*")

        return "\n".join(lines)

    def log_report(self, only_errors=True, exc_info=True):
        report = self.get_report(only_errors, exc_info)
        if report:
            log.info(report)


class PluginDiscoverContext(object):
    """Store and discover registered types nad registered paths to types.

    Keeps in memory all registered types and their paths. Paths are dynamically
    loaded on discover so different discover calls won't return the same
    class objects even if were loaded from same file.
    """

    def __init__(self):
        self._registered_plugins = {}
        self._registered_plugin_paths = {}
        self._last_discovered_plugins = {}
        # Store the last result to memory
        self._last_discovered_results = {}

    def get_last_discovered_plugins(self, superclass):
        """Access last discovered plugin by a subperclass.

        Returns:
            None: When superclass was not discovered yet.
            list: Lastly discovered plugins of the superclass.
        """

        return self._last_discovered_plugins.get(superclass)

    def discover(
        self,
        superclass,
        allow_duplicates=True,
        ignore_classes=None,
        return_report=False
    ):
        """Find and return subclasses of `superclass`

        Args:
            superclass (type): Class which determines discovered subclasses.
            allow_duplicates (bool): Validate class name duplications.
            ignore_classes (list): List of classes that will be ignored
                and not added to result.

        Returns:
            DiscoverResult: Object holding succesfully discovered plugins,
                ignored plugins, plugins with missing abstract implementation
                and duplicated plugin.
        """

        if not ignore_classes:
            ignore_classes = []

        result = DiscoverResult(superclass)
        plugin_names = set()
        registered_classes = self._registered_plugins.get(superclass) or []
        registered_paths = self._registered_plugin_paths.get(superclass) or []
        for cls in registered_classes:
            if cls is superclass or cls in ignore_classes:
                result.ignored_plugins.add(cls)
                continue

            if inspect.isabstract(cls):
                result.abstract_plugins.append(cls)
                continue

            class_name = cls.__name__
            if class_name in plugin_names:
                result.duplicated_plugins.append(cls)
                continue
            plugin_names.add(class_name)
            result.plugins.append(cls)

        # Include plug-ins from registered paths
        for path in registered_paths:
            modules, crashed = modules_from_path(path)
            for item in crashed:
                filepath, exc_info = item
                result.crashed_file_paths[filepath] = exc_info

            for item in modules:
                filepath, module = item
                result.add_module(module)
                for cls in classes_from_module(superclass, module):
                    if cls is superclass or cls in ignore_classes:
                        result.ignored_plugins.add(cls)
                        continue

                    if inspect.isabstract(cls):
                        result.abstract_plugins.append(cls)
                        continue

                    if not allow_duplicates:
                        class_name = cls.__name__
                        if class_name in plugin_names:
                            result.duplicated_plugins.append(cls)
                            continue
                        plugin_names.add(class_name)

                    result.plugins.append(cls)

        # Store in memory last result to keep in memory loaded modules
        self._last_discovered_results[superclass] = result
        self._last_discovered_plugins[superclass] = list(
            result.plugins
        )
        result.log_report()
        if return_report:
            return result
        return result.plugins

    def register_plugin(self, superclass, cls):
        """Register a directory containing plug-ins of type `superclass`

        Arguments:
            superclass (type): Superclass of plug-in
            cls (object): Subclass of `superclass`
        """

        if superclass not in self._registered_plugins:
            self._registered_plugins[superclass] = list()

        if cls not in self._registered_plugins[superclass]:
            self._registered_plugins[superclass].append(cls)

    def register_plugin_path(self, superclass, path):
        """Register a directory of one or more plug-ins

        Arguments:
            superclass (type): Superclass of plug-ins to look for during
                discovery
            path (str): Absolute path to directory in which to discover
                plug-ins
        """

        if superclass not in self._registered_plugin_paths:
            self._registered_plugin_paths[superclass] = list()

        path = os.path.normpath(path)
        if path not in self._registered_plugin_paths[superclass]:
            self._registered_plugin_paths[superclass].append(path)

    def registered_plugin_paths(self):
        """Return all currently registered plug-in paths"""
        # Return shallow copy so we the original data can't be changed
        return {
            superclass: paths[:]
            for superclass, paths in self._registered_plugin_paths.items()
        }

    def deregister_plugin(self, superclass, plugin):
        """Opposite of `register_plugin()`"""
        if superclass in self._registered_plugins:
            self._registered_plugins[superclass].remove(plugin)

    def deregister_plugin_path(self, superclass, path):
        """Opposite of `register_plugin_path()`"""
        self._registered_plugin_paths[superclass].remove(path)


class _GlobalDiscover:
    """Access to global object of PluginDiscoverContext.

    Using singleton object to register/deregister plugins and plugin paths
    and then discover them by superclass.
    """

    _context = None

    @classmethod
    def get_context(cls):
        if cls._context is None:
            cls._context = PluginDiscoverContext()
        return cls._context


def discover(superclass, allow_duplicates=True):
    context = _GlobalDiscover.get_context()
    return context.discover(superclass, allow_duplicates)


def get_last_discovered_plugins(superclass):
    context = _GlobalDiscover.get_context()
    return context.get_last_discovered_plugins(superclass)


def register_plugin(superclass, cls):
    context = _GlobalDiscover.get_context()
    context.register_plugin(superclass, cls)


def register_plugin_path(superclass, path):
    context = _GlobalDiscover.get_context()
    context.register_plugin_path(superclass, path)


def deregister_plugin(superclass, cls):
    context = _GlobalDiscover.get_context()
    context.deregister_plugin(superclass, cls)


def deregister_plugin_path(superclass, path):
    context = _GlobalDiscover.get_context()
    context.deregister_plugin_path(superclass, path)
