# -*- coding: utf-8 -*-
"""Pype module."""
import os
import platform
import functools
import logging

from openpype.pipeline import (
    LegacyCreator,
    register_loader_plugins_path,
    deregister_loader_plugins_path,
)

from .settings import get_project_settings
from .lib import (
    Anatomy,
    filter_pyblish_plugins,
    set_plugin_attributes_from_settings,
    change_timer_to_current_context
)

pyblish = avalon = _original_discover = None

log = logging.getLogger(__name__)


PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

# Global plugin paths
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")


def import_wrapper(func):
    """Wrap module imports to specific functions."""
    @functools.wraps(func)
    def decorated(*args, **kwargs):
        global pyblish
        global avalon
        global _original_discover
        if pyblish is None:
            from pyblish import api as pyblish
            from avalon import api as avalon

            # we are monkey patching `avalon.api.discover()` to allow us to
            # load plugin presets on plugins being discovered by avalon.
            # Little bit of hacking, but it allows us to add out own features
            # without need to modify upstream code.

            _original_discover = avalon.discover

        return func(*args, **kwargs)

    return decorated


@import_wrapper
def patched_discover(superclass):
    """Patch `avalon.api.discover()`.

    Monkey patched version of :func:`avalon.api.discover()`. It allows
    us to load presets on plugins being discovered.
    """
    # run original discover and get plugins
    plugins = _original_discover(superclass)
    filtered_plugins = [
        plugin
        for plugin in plugins
        if issubclass(plugin, superclass)
    ]

    set_plugin_attributes_from_settings(filtered_plugins, superclass)

    return filtered_plugins


@import_wrapper
def install():
    """Install Pype to Avalon."""
    from pyblish.lib import MessageHandler
    from openpype.modules import load_modules
    from avalon import pipeline

    # Make sure modules are loaded
    load_modules()

    def modified_emit(obj, record):
        """Method replacing `emit` in Pyblish's MessageHandler."""
        record.msg = record.getMessage()
        obj.records.append(record)

    MessageHandler.emit = modified_emit

    log.info("Registering global plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    pyblish.register_discovery_filter(filter_pyblish_plugins)
    register_loader_plugins_path(LOAD_PATH)

    project_name = os.environ.get("AVALON_PROJECT")

    # Register studio specific plugins
    if project_name:
        anatomy = Anatomy(project_name)
        anatomy.set_root_environments()
        avalon.register_root(anatomy.roots)

        project_settings = get_project_settings(project_name)
        platform_name = platform.system().lower()
        project_plugins = (
            project_settings
            .get("global", {})
            .get("project_plugins", {})
            .get(platform_name)
        ) or []
        for path in project_plugins:
            try:
                path = str(path.format(**os.environ))
            except KeyError:
                pass

            if not path or not os.path.exists(path):
                continue

            pyblish.register_plugin_path(path)
            register_loader_plugins_path(path)
            avalon.register_plugin_path(LegacyCreator, path)
            avalon.register_plugin_path(avalon.InventoryAction, path)

    # apply monkey patched discover to original one
    log.info("Patching discovery")

    avalon.discover = patched_discover
    pipeline.discover = patched_discover

    avalon.on("taskChanged", _on_task_change)


def _on_task_change(*args):
    change_timer_to_current_context()


@import_wrapper
def uninstall():
    """Uninstall Pype from Avalon."""
    log.info("Deregistering global plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    pyblish.deregister_discovery_filter(filter_pyblish_plugins)
    deregister_loader_plugins_path(LOAD_PATH)
    log.info("Global plug-ins unregistred")

    # restore original discover
    avalon.discover = _original_discover
