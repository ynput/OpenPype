import os
import sys
import types

import six
import pyblish.plugin


class DiscoverResult:
    """Hold result of publish plugins discovery.

    Stores discovered plugins duplicated plugins and file paths which
    crashed on execution of file.
    """
    def __init__(self):
        self.plugins = []
        self.crashed_file_paths = {}
        self.duplicated_plugins = []

    def __iter__(self):
        for plugin in self.plugins:
            yield plugin

    def __getitem__(self, item):
        return self.plugins[item]

    def __setitem__(self, item, value):
        self.plugins[item] = value


def publish_plugins_discover(paths=None):
    """Find and return available pyblish plug-ins

    Overriden function from `pyblish` module to be able collect crashed files
    and reason of their crash.

    Arguments:
        paths (list, optional): Paths to discover plug-ins from.
            If no paths are provided, all paths are searched.

    """

    # The only difference with `pyblish.api.discover`
    result = DiscoverResult()

    plugins = dict()
    plugin_names = []

    allow_duplicates = pyblish.plugin.ALLOW_DUPLICATES
    log = pyblish.plugin.log

    # Include plug-ins from registered paths
    if not paths:
        paths = pyblish.plugin.plugin_paths()

    for path in paths:
        path = os.path.normpath(path)
        if not os.path.isdir(path):
            continue

        for fname in os.listdir(path):
            if fname.startswith("_"):
                continue

            abspath = os.path.join(path, fname)

            if not os.path.isfile(abspath):
                continue

            mod_name, mod_ext = os.path.splitext(fname)

            if not mod_ext == ".py":
                continue

            module = types.ModuleType(mod_name)
            module.__file__ = abspath

            try:
                with open(abspath, "rb") as f:
                    six.exec_(f.read(), module.__dict__)

                # Store reference to original module, to avoid
                # garbage collection from collecting it's global
                # imports, such as `import os`.
                sys.modules[abspath] = module

            except Exception as err:
                result.crashed_file_paths[abspath] = sys.exc_info()

                log.debug("Skipped: \"%s\" (%s)", mod_name, err)
                continue

            for plugin in pyblish.plugin.plugins_from_module(module):
                if not allow_duplicates and plugin.__name__ in plugin_names:
                    result.duplicated_plugins.append(plugin)
                    log.debug("Duplicate plug-in found: %s", plugin)
                    continue

                plugin_names.append(plugin.__name__)

                plugin.__module__ = module.__file__
                key = "{0}.{1}".format(plugin.__module__, plugin.__name__)
                plugins[key] = plugin

    # Include plug-ins from registration.
    # Directly registered plug-ins take precedence.
    for plugin in pyblish.plugin.registered_plugins():
        if not allow_duplicates and plugin.__name__ in plugin_names:
            result.duplicated_plugins.append(plugin)
            log.debug("Duplicate plug-in found: %s", plugin)
            continue

        plugin_names.append(plugin.__name__)

        plugins[plugin.__name__] = plugin

    plugins = list(plugins.values())
    pyblish.plugin.sort(plugins)  # In-place

    # In-place user-defined filter
    for filter_ in pyblish.plugin._registered_plugin_filters:
        filter_(plugins)

    result.plugins = plugins

    return result
