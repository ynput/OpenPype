import os
import sys
import types
import inspect
import xml.etree.ElementTree

import six
import pyblish.plugin
import pyblish.api

from openpype.lib import Logger
from openpype.settings import get_project_settings, get_system_settings


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


class HelpContent:
    def __init__(self, title, description, detail=None):
        self.title = title
        self.description = description
        self.detail = detail


def load_help_content_from_filepath(filepath):
    """Load help content from xml file.
    Xml file may containt errors and warnings.
    """
    errors = {}
    warnings = {}
    output = {
        "errors": errors,
        "warnings": warnings
    }
    if not os.path.exists(filepath):
        return output
    tree = xml.etree.ElementTree.parse(filepath)
    root = tree.getroot()
    for child in root:
        child_id = child.attrib.get("id")
        if child_id is None:
            continue

        # Make sure ID is string
        child_id = str(child_id)

        title = child.find("title").text
        description = child.find("description").text
        detail_node = child.find("detail")
        detail = None
        if detail_node is not None:
            detail = detail_node.text
        if child.tag == "error":
            errors[child_id] = HelpContent(title, description, detail)
        elif child.tag == "warning":
            warnings[child_id] = HelpContent(title, description, detail)
    return output


def load_help_content_from_plugin(plugin):
    cls = plugin
    if not inspect.isclass(plugin):
        cls = plugin.__class__
    plugin_filepath = inspect.getfile(cls)
    plugin_dir = os.path.dirname(plugin_filepath)
    basename = os.path.splitext(os.path.basename(plugin_filepath))[0]
    filename = basename + ".xml"
    filepath = os.path.join(plugin_dir, "help", filename)
    return load_help_content_from_filepath(filepath)


def publish_plugins_discover(paths=None):
    """Find and return available pyblish plug-ins

    Overridden function from `pyblish` module to be able collect crashed files
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


def filter_pyblish_plugins(plugins):
    """Pyblish plugin filter which applies OpenPype settings.

    Apply OpenPype settings on discovered plugins. On plugin with implemented
    class method 'def apply_settings(cls, project_settings, system_settings)'
    is called the method. Default behavior looks for plugin name and current
    host name to look for

    Args:
        plugins (List[pyblish.plugin.Plugin]): Discovered plugins on which
            are applied settings.
    """

    log = Logger.get_logger("filter_pyblish_plugins")

    # TODO: Don't use host from 'pyblish.api' but from defined host by us.
    #   - kept becau on farm is probably used host 'shell' which propably
    #       affect how settings are applied there
    host = pyblish.api.current_host()
    project_name = os.environ.get("AVALON_PROJECT")

    project_setting = get_project_settings(project_name)
    system_settings = get_system_settings()

    # iterate over plugins
    for plugin in plugins[:]:
        if hasattr(plugin, "apply_settings"):
            try:
                # Use classmethod 'apply_settings'
                # - can be used to target settings from custom settings place
                # - skip default behavior when successful
                plugin.apply_settings(project_setting, system_settings)
                continue

            except Exception:
                log.warning(
                    (
                        "Failed to apply settings on plugin {}"
                    ).format(plugin.__name__),
                    exc_info=True
                )

        try:
            config_data = (
                project_setting
                [host]
                ["publish"]
                [plugin.__name__]
            )
        except KeyError:
            # host determined from path
            file = os.path.normpath(inspect.getsourcefile(plugin))
            file = os.path.normpath(file)

            split_path = file.split(os.path.sep)
            if len(split_path) < 4:
                log.warning(
                    'plugin path too short to extract host {}'.format(file)
                )
                continue

            host_from_file = split_path[-4]
            plugin_kind = split_path[-2]

            # TODO: change after all plugins are moved one level up
            if host_from_file == "openpype":
                host_from_file = "global"

            try:
                config_data = (
                    project_setting
                    [host_from_file]
                    [plugin_kind]
                    [plugin.__name__]
                )
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


def find_close_plugin(close_plugin_name, log):
    if close_plugin_name:
        plugins = pyblish.api.discover()
        for plugin in plugins:
            if plugin.__name__ == close_plugin_name:
                return plugin

    log.debug("Close plugin not found, app might not close.")


def remote_publish(log, close_plugin_name=None, raise_error=False):
    """Loops through all plugins, logs to console. Used for tests.

        Args:
            log (openpype.lib.Logger)
            close_plugin_name (str): name of plugin with responsibility to
                close host app
    """
    # Error exit as soon as any error occurs.
    error_format = "Failed {plugin.__name__}: {error} -- {error.traceback}"

    close_plugin = find_close_plugin(close_plugin_name, log)

    for result in pyblish.util.publish_iter():
        for record in result["records"]:
            log.info("{}: {}".format(
                result["plugin"].label, record.msg))

        if result["error"]:
            error_message = error_format.format(**result)
            log.error(error_message)
            if close_plugin:  # close host app explicitly after error
                context = pyblish.api.Context()
                close_plugin().process(context)
            if raise_error:
                # Fatal Error is because of Deadline
                error_message = "Fatal Error: " + error_format.format(**result)
                raise RuntimeError(error_message)


def get_errored_instances_from_context(context):
    """Collect failed instances from pyblish context.

    Args:
        context (pyblish.api.Context): Publish context where we're looking
            for failed instances.

    Returns:
        List[pyblish.lib.Instance]: Instances which failed during processing.
    """

    instances = list()
    for result in context.data["results"]:
        if result["instance"] is None:
            # When instance is None we are on the "context" result
            continue

        if result["error"]:
            instances.append(result["instance"])

    return instances


def get_errored_plugins_from_context(context):
    """Collect failed plugins from pyblish context.

    Args:
        context (pyblish.api.Context): Publish context where we're looking
            for failed plugins.

    Returns:
        List[pyblish.api.Plugin]: Plugins which failed during processing.
    """

    plugins = list()
    results = context.data.get("results", [])
    for result in results:
        if result["success"] is True:
            continue
        plugins.append(result["plugin"])

    return plugins
