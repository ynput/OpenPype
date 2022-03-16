# -*- coding: utf-8 -*-
"""Avalon/Pyblish plugin tools."""
import os
import inspect
import logging
import re
import json

from .profiles_filtering import filter_profiles

from openpype.settings import get_project_settings


log = logging.getLogger(__name__)

# Subset name template used when plugin does not have defined any
DEFAULT_SUBSET_TEMPLATE = "{family}{Variant}"


class TaskNotSetError(KeyError):
    def __init__(self, msg=None):
        if not msg:
            msg = "Creator's subset name template requires task name."
        super(TaskNotSetError, self).__init__(msg)


def get_subset_name_with_asset_doc(
    family,
    variant,
    task_name,
    asset_doc,
    project_name=None,
    host_name=None,
    default_template=None,
    dynamic_data=None
):
    """Calculate subset name based on passed context and OpenPype settings.

    Subst name templates are defined in `project_settings/global/tools/creator
    /subset_name_profiles` where are profiles with host name, family, task name
    and task type filters. If context does not match any profile then
    `DEFAULT_SUBSET_TEMPLATE` is used as default template.

    That's main reason why so many arguments are required to calculate subset
    name.

    Args:
        family (str): Instance family.
        variant (str): In most of cases it is user input during creation.
        task_name (str): Task name on which context is instance created.
        asset_doc (dict): Queried asset document with it's tasks in data.
            Used to get task type.
        project_name (str): Name of project on which is instance created.
            Important for project settings that are loaded.
        host_name (str): One of filtering criteria for template profile
            filters.
        default_template (str): Default template if any profile does not match
            passed context. Constant 'DEFAULT_SUBSET_TEMPLATE' is used if
            is not passed.
        dynamic_data (dict): Dynamic data specific for a creator which creates
            instance.
        dbcon (AvalonMongoDB): Mongo connection to be able query asset document
            if 'asset_doc' is not passed.
    """
    if not family:
        return ""

    if not host_name:
        host_name = os.environ["AVALON_APP"]

    # Use only last part of class family value split by dot (`.`)
    family = family.rsplit(".", 1)[-1]

    if project_name is None:
        import avalon.api

        project_name = avalon.api.Session["AVALON_PROJECT"]

    asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
    task_info = asset_tasks.get(task_name) or {}
    task_type = task_info.get("type")

    # Get settings
    tools_settings = get_project_settings(project_name)["global"]["tools"]
    profiles = tools_settings["creator"]["subset_name_profiles"]
    filtering_criteria = {
        "families": family,
        "hosts": host_name,
        "tasks": task_name,
        "task_types": task_type
    }

    matching_profile = filter_profiles(profiles, filtering_criteria)
    template = None
    if matching_profile:
        template = matching_profile["template"]

    # Make sure template is set (matching may have empty string)
    if not template:
        template = default_template or DEFAULT_SUBSET_TEMPLATE

    # Simple check of task name existence for template with {task} in
    #   - missing task should be possible only in Standalone publisher
    if not task_name and "{task" in template.lower():
        raise TaskNotSetError()

    fill_pairs = {
        "variant": variant,
        "family": family,
        "task": task_name
    }
    if dynamic_data:
        # Dynamic data may override default values
        for key, value in dynamic_data.items():
            fill_pairs[key] = value

    return template.format(**prepare_template_data(fill_pairs))


def get_subset_name(
    family,
    variant,
    task_name,
    asset_id,
    project_name=None,
    host_name=None,
    default_template=None,
    dynamic_data=None,
    dbcon=None
):
    """Calculate subset name using OpenPype settings.

    This variant of function expects asset id as argument.

    This is legacy function should be replaced with
    `get_subset_name_with_asset_doc` where asset document is expected.
    """
    if dbcon is None:
        from avalon.api import AvalonMongoDB

        dbcon = AvalonMongoDB()
        dbcon.Session["AVALON_PROJECT"] = project_name

    dbcon.install()

    asset_doc = dbcon.find_one(
        {"_id": asset_id},
        {"data.tasks": True}
    ) or {}

    return get_subset_name_with_asset_doc(
        family,
        variant,
        task_name,
        asset_doc,
        project_name,
        host_name,
        default_template,
        dynamic_data
    )


def prepare_template_data(fill_pairs):
    """
        Prepares formatted data for filling template.

        It produces multiple variants of keys (key, Key, KEY) to control
        format of filled template.

        Args:
            fill_pairs (iterable) of tuples (key, value)
        Returns:
            (dict)
            ('host', 'maya') > {'host':'maya', 'Host': 'Maya', 'HOST': 'MAYA'}

    """
    fill_data = {}
    regex = re.compile(r"[a-zA-Z0-9]")
    for key, value in dict(fill_pairs).items():
        # Handle cases when value is `None` (standalone publisher)
        if value is None:
            continue
        # Keep value as it is
        fill_data[key] = value
        # Both key and value are with upper case
        fill_data[key.upper()] = value.upper()

        # Capitalize only first char of value
        # - conditions are because of possible index errors
        # - regex is to skip symbols that are not chars or numbers
        #   - e.g. "{key}" which starts with curly bracket
        capitalized = ""
        for idx in range(len(value or "")):
            char = value[idx]
            if not regex.match(char):
                capitalized += char
            else:
                capitalized += char.upper()
                capitalized += value[idx + 1:]
                break

        fill_data[key.capitalize()] = capitalized

    return fill_data


def filter_pyblish_plugins(plugins):
    """Filter pyblish plugins by presets.

    This servers as plugin filter / modifier for pyblish. It will load plugin
    definitions from presets and filter those needed to be excluded.

    Args:
        plugins (dict): Dictionary of plugins produced by :mod:`pyblish-base`
            `discover()` method.

    """
    from pyblish import api

    host = api.current_host()

    presets = get_project_settings(os.environ['AVALON_PROJECT']) or {}
    # skip if there are no presets to process
    if not presets:
        return

    # iterate over plugins
    for plugin in plugins[:]:

        try:
            config_data = presets[host]["publish"][plugin.__name__]
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


def set_plugin_attributes_from_settings(
    plugins, superclass, host_name=None, project_name=None
):
    """Change attribute values on Avalon plugins by project settings.

    This function should be used only in host context. Modify
    behavior of plugins.

    Args:
        plugins (list): Plugins discovered by origin avalon discover method.
        superclass (object): Superclass of plugin type (e.g. Cretor, Loader).
        host_name (str): Name of host for which plugins are loaded and from.
            Value from environment `AVALON_APP` is used if not entered.
        project_name (str): Name of project for which settings will be loaded.
            Value from environment `AVALON_PROJECT` is used if not entered.
    """

    # determine host application to use for finding presets
    if host_name is None:
        host_name = os.environ.get("AVALON_APP")

    if project_name is None:
        project_name = os.environ.get("AVALON_PROJECT")

    # map plugin superclass to preset json. Currently supported is load and
    # create (avalon.api.Loader and avalon.api.Creator)
    plugin_type = None
    if superclass.__name__.split(".")[-1] in ("Loader", "SubsetLoader"):
        plugin_type = "load"
    elif superclass.__name__.split(".")[-1] in ("Creator", "LegacyCreator"):
        plugin_type = "create"

    if not host_name or not project_name or plugin_type is None:
        msg = "Skipped attributes override from settings."
        if not host_name:
            msg += " Host name is not defined."

        if not project_name:
            msg += " Project name is not defined."

        if plugin_type is None:
            msg += " Plugin type is unsupported for class {}.".format(
                superclass.__name__
            )

        print(msg)
        return

    print(">>> Finding presets for {}:{} ...".format(host_name, plugin_type))

    project_settings = get_project_settings(project_name)
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

    for plugin in plugins:
        plugin_name = plugin.__name__

        plugin_settings = None
        # Look for plugin settings in host specific settings
        if plugin_name in plugin_type_settings:
            plugin_settings = plugin_type_settings[plugin_name]

        # Look for plugin settings in global settings
        elif plugin_name in global_type_settings:
            plugin_settings = global_type_settings[plugin_name]

        if not plugin_settings:
            continue

        print(">>> We have preset for {}".format(plugin_name))
        for option, value in plugin_settings.items():
            if option == "enabled" and value is False:
                setattr(plugin, "active", False)
                print("  - is disabled by preset")
            else:
                setattr(plugin, option, value)
                print("  - setting `{}`: `{}`".format(option, value))


def source_hash(filepath, *args):
    """Generate simple identifier for a source file.
    This is used to identify whether a source file has previously been
    processe into the pipeline, e.g. a texture.
    The hash is based on source filepath, modification time and file size.
    This is only used to identify whether a specific source file was already
    published before from the same location with the same modification date.
    We opt to do it this way as opposed to Avalanch C4 hash as this is much
    faster and predictable enough for all our production use cases.
    Args:
        filepath (str): The source file path.
    You can specify additional arguments in the function
    to allow for specific 'processing' values to be included.
    """
    # We replace dots with comma because . cannot be a key in a pymongo dict.
    file_name = os.path.basename(filepath)
    time = str(os.path.getmtime(filepath))
    size = str(os.path.getsize(filepath))
    return "|".join([file_name, time, size] + list(args)).replace(".", ",")


def get_unique_layer_name(layers, name):
    """
        Gets all layer names and if 'name' is present in them, increases
        suffix by 1 (eg. creates unique layer name - for Loader)
    Args:
        layers (list): of strings, names only
        name (string):  checked value

    Returns:
        (string): name_00X (without version)
    """
    names = {}
    for layer in layers:
        layer_name = re.sub(r'_\d{3}$', '', layer)
        if layer_name in names.keys():
            names[layer_name] = names[layer_name] + 1
        else:
            names[layer_name] = 1
    occurrences = names.get(name, 0)

    return "{}_{:0>3d}".format(name, occurrences + 1)


def get_background_layers(file_url):
    """
        Pulls file name from background json file, enrich with folder url for
        AE to be able import files.

        Order is important, follows order in json.

        Args:
            file_url (str): abs url of background json

        Returns:
            (list): of abs paths to images
    """
    with open(file_url) as json_file:
        data = json.load(json_file)

    layers = list()
    bg_folder = os.path.dirname(file_url)
    for child in data['children']:
        if child.get("filename"):
            layers.append(os.path.join(bg_folder, child.get("filename")).
                          replace("\\", "/"))
        else:
            for layer in child['children']:
                if layer.get("filename"):
                    layers.append(os.path.join(bg_folder,
                                               layer.get("filename")).
                                  replace("\\", "/"))
    return layers


def parse_json(path):
    """Parses json file at 'path' location

        Returns:
            (dict) or None if unparsable
        Raises:
            AsssertionError if 'path' doesn't exist
    """
    path = path.strip('\"')
    assert os.path.isfile(path), (
        "Path to json file doesn't exist. \"{}\"".format(path)
    )
    data = None
    with open(path, "r") as json_file:
        try:
            data = json.load(json_file)
        except Exception as exc:
            log.error(
                "Error loading json: "
                "{} - Exception: {}".format(path, exc)
            )
    return data


def get_batch_asset_task_info(ctx):
    """Parses context data from webpublisher's batch metadata

        Returns:
            (tuple): asset, task_name (Optional), task_type
    """
    task_type = "default_task_type"
    task_name = None
    asset = None

    if ctx["type"] == "task":
        items = ctx["path"].split('/')
        asset = items[-2]
        task_name = ctx["name"]
        task_type = ctx["attributes"]["type"]
    else:
        asset = ctx["name"]

    return asset, task_name, task_type
