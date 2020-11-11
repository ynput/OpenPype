# -*- coding: utf-8 -*-
"""Avalon/Pyblish plugin tools."""
import os
import inspect
import logging

from ..api import config


log = logging.getLogger(__name__)


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
