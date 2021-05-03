# -*- coding: utf-8 -*-
"""Avalon/Pyblish plugin tools."""
import os
import inspect
import logging
import re
import json
import tempfile

from .execute import run_subprocess
from .profiles_filtering import filter_profiles
from .vendor_bin_utils import get_oiio_tools_path

from openpype.settings import get_project_settings


log = logging.getLogger(__name__)

# Subset name template used when plugin does not have defined any
DEFAULT_SUBSET_TEMPLATE = "{family}{Variant}"


class TaskNotSetError(KeyError):
    def __init__(self, msg=None):
        if not msg:
            msg = "Creator's subset name template requires task name."
        super(TaskNotSetError, self).__init__(msg)


def get_subset_name(
    family,
    variant,
    task_name,
    asset_id,
    project_name=None,
    host_name=None,
    default_template=None
):
    if not family:
        return ""

    if not host_name:
        host_name = os.environ["AVALON_APP"]

    # Use only last part of class family value split by dot (`.`)
    family = family.rsplit(".", 1)[-1]

    # Get settings
    tools_settings = get_project_settings(project_name)["global"]["tools"]
    profiles = tools_settings["creator"]["subset_name_profiles"]
    filtering_criteria = {
        "families": family,
        "hosts": host_name,
        "tasks": task_name
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

    fill_pairs = (
        ("variant", variant),
        ("family", family),
        ("task", task_name)
    )
    fill_data = {}
    for key, value in fill_pairs:
        # Handle cases when value is `None` (standalone publisher)
        if value is None:
            continue
        # Keep value as it is
        fill_data[key] = value
        # Both key and value are with upper case
        fill_data[key.upper()] = value.upper()

        # Capitalize only first char of value
        # - conditions are because of possible index errors
        capitalized = ""
        if value:
            # Upper first character
            capitalized += value[0].upper()
            # Append rest of string if there is any
            if len(value) > 1:
                capitalized += value[1:]
        fill_data[key.capitalize()] = capitalized

    return template.format(**fill_data)


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

        file = os.path.normpath(inspect.getsourcefile(plugin))
        file = os.path.normpath(file)

        # host determined from path
        host_from_file = file.split(os.path.sep)[-4:-3][0]
        plugin_kind = file.split(os.path.sep)[-2:-1][0]

        # TODO: change after all plugins are moved one level up
        if host_from_file == "openpype":
            host_from_file = "global"

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

    # map plugin superclass to preset json. Currenly suppoted is load and
    # create (avalon.api.Loader and avalon.api.Creator)
    plugin_type = None
    if superclass.__name__.split(".")[-1] == "Loader":
        plugin_type = "load"
    elif superclass.__name__.split(".")[-1] == "Creator":
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


def oiio_supported():
    """
        Checks if oiiotool is configured for this platform.

        Expects full path to executable.

        'should_decompress' will throw exception if configured,
        but not present or not working.
        Returns:
            (bool)
    """
    oiio_path = get_oiio_tools_path()
    if not oiio_path or not os.path.exists(oiio_path):
        log.debug("OIIOTool is not configured or not present at {}".
                  format(oiio_path))
        return False

    return True


def decompress(target_dir, file_url,
               input_frame_start=None, input_frame_end=None, log=None):
    """
        Decompresses DWAA 'file_url' .exr to 'target_dir'.

        Creates uncompressed files in 'target_dir', they need to be cleaned.

        File url could be for single file or for a sequence, in that case
        %0Xd will be as a placeholder for frame number AND input_frame* will
        be filled.
        In that case single oiio command with '--frames' will be triggered for
        all frames, this should be faster then looping and running sequentially

        Args:
            target_dir (str): extended from stagingDir
            file_url (str): full urls to source file (with or without %0Xd)
            input_frame_start (int) (optional): first frame
            input_frame_end (int) (optional): last frame
            log (Logger) (optional): pype logger
    """
    is_sequence = input_frame_start is not None and \
        input_frame_end is not None and \
        (int(input_frame_end) > int(input_frame_start))

    oiio_cmd = []
    oiio_cmd.append(get_oiio_tools_path())

    oiio_cmd.append("--compression none")

    base_file_name = os.path.basename(file_url)
    oiio_cmd.append(file_url)

    if is_sequence:
        oiio_cmd.append("--frames {}-{}".format(input_frame_start,
                                                input_frame_end))

    oiio_cmd.append("-o")
    oiio_cmd.append(os.path.join(target_dir, base_file_name))

    subprocess_exr = " ".join(oiio_cmd)

    if not log:
        log = logging.getLogger(__name__)

    log.debug("Decompressing {}".format(subprocess_exr))
    run_subprocess(
        subprocess_exr, shell=True, logger=log
    )


def get_decompress_dir():
    """
        Creates temporary folder for decompressing.
        Its local, in case of farm it is 'local' to the farm machine.

        Should be much faster, needs to be cleaned up later.
    """
    return os.path.normpath(
        tempfile.mkdtemp(prefix="pyblish_tmp_")
    )


def should_decompress(file_url):
    """
        Tests that 'file_url' is compressed with DWAA.

        Uses 'oiio_supported' to check that OIIO tool is available for this
        platform.

        Shouldn't throw exception as oiiotool is guarded by check function.
        Currently implemented this way as there is no support for Mac and Linux
        In the future, it should be more strict and throws exception on
        misconfiguration.

        Args:
            file_url (str): path to rendered file (in sequence it would be
                first file, if that compressed it is expected that whole seq
                will be too)
        Returns:
            (bool): 'file_url' is DWAA compressed and should be decompressed
                and we can decompress (oiiotool supported)
    """
    if oiio_supported():
        output = run_subprocess([
            get_oiio_tools_path(),
            "--info", "-v", file_url])
        return "compression: \"dwaa\"" in output or \
            "compression: \"dwab\"" in output

    return False
