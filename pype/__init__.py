# -*- coding: utf-8 -*-
"""Pype module."""
import os
import functools
import logging

from .settings import get_project_settings
from .lib import Anatomy, filter_pyblish_plugins, \
    change_timer_to_current_context

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

    # determine host application to use for finding presets
    if avalon.registered_host() is None:
        return plugins
    host = avalon.registered_host().__name__.split(".")[-1]

    # map plugin superclass to preset json. Currenly suppoted is load and
    # create (avalon.api.Loader and avalon.api.Creator)
    plugin_type = "undefined"
    if superclass.__name__.split(".")[-1] == "Loader":
        plugin_type = "load"
    elif superclass.__name__.split(".")[-1] == "Creator":
        plugin_type = "create"

    print(">>> Finding presets for {}:{} ...".format(host, plugin_type))
    try:
        settings = (
            get_project_settings(os.environ['AVALON_PROJECT'])
            [host][plugin_type]
        )
    except KeyError:
        print("*** no presets found.")
    else:
        for plugin in plugins:
            if plugin.__name__ in settings:
                print(">>> We have preset for {}".format(plugin.__name__))
                for option, value in settings[plugin.__name__].items():
                    if option == "enabled" and value is False:
                        setattr(plugin, "active", False)
                        print("  - is disabled by preset")
                    else:
                        setattr(plugin, option, value)
                        print("  - setting `{}`: `{}`".format(option, value))
    return plugins


@import_wrapper
def install():
    """Install Pype to Avalon."""
    log.info("Registering global plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    pyblish.register_discovery_filter(filter_pyblish_plugins)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)

    project_name = os.environ.get("AVALON_PROJECT")

    if project_name:
        anatomy = Anatomy(project_name)
        anatomy.set_root_environments()
        avalon.register_root(anatomy.roots)
    # apply monkey patched discover to original one
    log.info("Patching discovery")
    avalon.discover = patched_discover

    avalon.on("taskChanged", _on_task_change)


def _on_task_change(*args):
    change_timer_to_current_context()


@import_wrapper
def uninstall():
    """Uninstall Pype from Avalon."""
    log.info("Deregistering global plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    pyblish.deregister_discovery_filter(filter_pyblish_plugins)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    log.info("Global plug-ins unregistred")

    # restore original discover
    avalon.discover = _original_discover
