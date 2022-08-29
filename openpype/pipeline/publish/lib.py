import os
import sys
import types
import inspect
import copy
import xml.etree.ElementTree

import six
import pyblish.plugin
import pyblish.api

from openpype.lib import Logger, filter_profiles
from openpype.settings import (
    get_project_settings,
    get_system_settings,
)

from .contants import (
    DEFAULT_PUBLISH_TEMPLATE,
    DEFAULT_HERO_PUBLISH_TEMPLATE,
)


def get_template_name_profiles(
    project_name, project_settings=None, logger=None
):
    """Receive profiles for publish template keys.

    At least one of arguments must be passed.

    Args:
        project_name (str): Name of project where to look for templates.
        project_settings(Dic[str, Any]): Prepared project settings.

    Returns:
        List[Dict[str, Any]]: Publish template profiles.
    """

    if not project_name and not project_settings:
        raise ValueError((
            "Both project name and project settings are missing."
            " At least one must be entered."
        ))

    if not project_settings:
        project_settings = get_project_settings(project_name)

    profiles = (
        project_settings
        ["global"]
        ["tools"]
        ["publish"]
        ["template_name_profiles"]
    )
    if profiles:
        return copy.deepcopy(profiles)

    # Use legacy approach for cases new settings are not filled yet for the
    #   project
    legacy_profiles = (
        project_settings
        ["global"]
        ["publish"]
        ["IntegrateAssetNew"]
        ["template_name_profiles"]
    )
    if legacy_profiles:
        if not logger:
            logger = Logger.get_logger("get_template_name_profiles")

        logger.warning((
            "Project \"{}\" is using legacy access to publish template."
            " It is recommended to move settings to new location"
            " 'project_settings/global/tools/publish/template_name_profiles'."
        ).format(project_name))

    # Replace "tasks" key with "task_names"
    profiles = []
    for profile in copy.deepcopy(legacy_profiles):
        profile["task_names"] = profile.pop("tasks", [])
        profiles.append(profile)
    return profiles


def get_hero_template_name_profiles(
    project_name, project_settings=None, logger=None
):
    """Receive profiles for hero publish template keys.

    At least one of arguments must be passed.

    Args:
        project_name (str): Name of project where to look for templates.
        project_settings(Dic[str, Any]): Prepared project settings.

    Returns:
        List[Dict[str, Any]]: Publish template profiles.
    """

    if not project_name and not project_settings:
        raise ValueError((
            "Both project name and project settings are missing."
            " At least one must be entered."
        ))

    if not project_settings:
        project_settings = get_project_settings(project_name)

    profiles = (
        project_settings
        ["global"]
        ["tools"]
        ["publish"]
        ["hero_template_name_profiles"]
    )
    if profiles:
        return copy.deepcopy(profiles)

    # Use legacy approach for cases new settings are not filled yet for the
    #   project
    legacy_profiles = copy.deepcopy(
        project_settings
        ["global"]
        ["publish"]
        ["IntegrateHeroVersion"]
        ["template_name_profiles"]
    )
    if legacy_profiles:
        if not logger:
            logger = Logger.get_logger("get_hero_template_name_profiles")

        logger.warning((
            "Project \"{}\" is using legacy access to hero publish template."
            " It is recommended to move settings to new location"
            " 'project_settings/global/tools/publish/"
            "hero_template_name_profiles'."
        ).format(project_name))
    return legacy_profiles


def get_publish_template_name(
    project_name,
    host_name,
    family,
    task_name,
    task_type,
    project_settings=None,
    hero=False,
    logger=None
):
    """Get template name which should be used for passed context.

    Publish templates are filtered by host name, family, task name and
    task type.

    Default template which is used at if profiles are not available or profile
    has empty value is defined by 'DEFAULT_PUBLISH_TEMPLATE' constant.

    Args:
        project_name (str): Name of project where to look for settings.
        host_name (str): Name of host integration.
        family (str): Family for which should be found template.
        task_name (str): Task name on which is intance working.
        task_type (str): Task type on which is intance working.
        project_setting (Dict[str, Any]): Prepared project settings.
        logger (logging.Logger): Custom logger used for 'filter_profiles'
            function.

    Returns:
        str: Template name which should be used for integration.
    """

    template = None
    filter_criteria = {
        "hosts": host_name,
        "families": family,
        "task_names": task_name,
        "task_types": task_type,
    }
    if hero:
        default_template = DEFAULT_HERO_PUBLISH_TEMPLATE
        profiles = get_hero_template_name_profiles(
            project_name, project_settings, logger
        )

    else:
        profiles = get_template_name_profiles(
            project_name, project_settings, logger
        )
        default_template = DEFAULT_PUBLISH_TEMPLATE

    profile = filter_profiles(profiles, filter_criteria, logger=logger)
    if profile:
        template = profile["template_name"]
    return template or default_template


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
