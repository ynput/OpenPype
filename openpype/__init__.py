# -*- coding: utf-8 -*-
"""Pype module."""
import os
import platform
import logging

from .settings import get_project_settings
from .lib import (
    Anatomy,
    filter_pyblish_plugins,
    change_timer_to_current_context,
    register_event_callback,
)

log = logging.getLogger(__name__)


PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

# Global plugin paths
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")


def install():
    """Install OpenPype to Avalon."""
    import avalon.api
    import pyblish.api
    from pyblish.lib import MessageHandler
    from openpype.modules import load_modules
    from openpype.pipeline import (
        register_loader_plugin_path,
        register_inventory_action,
        register_creator_plugin_path,
    )

    # Make sure modules are loaded
    load_modules()

    def modified_emit(obj, record):
        """Method replacing `emit` in Pyblish's MessageHandler."""
        record.msg = record.getMessage()
        obj.records.append(record)

    MessageHandler.emit = modified_emit

    log.info("Registering global plug-ins..")
    pyblish.api.register_plugin_path(PUBLISH_PATH)
    pyblish.api.register_discovery_filter(filter_pyblish_plugins)
    register_loader_plugin_path(LOAD_PATH)

    project_name = os.environ.get("AVALON_PROJECT")

    # Register studio specific plugins
    if project_name:
        anatomy = Anatomy(project_name)
        anatomy.set_root_environments()
        avalon.api.register_root(anatomy.roots)

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

            pyblish.api.register_plugin_path(path)
            register_loader_plugin_path(path)
            register_creator_plugin_path(path)
            register_inventory_action(path)

    # apply monkey patched discover to original one
    log.info("Patching discovery")

    register_event_callback("taskChanged", _on_task_change)


def _on_task_change():
    change_timer_to_current_context()


def uninstall():
    """Uninstall Pype from Avalon."""
    import pyblish.api
    from openpype.pipeline import deregister_loader_plugin_path

    log.info("Deregistering global plug-ins..")
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    pyblish.api.deregister_discovery_filter(filter_pyblish_plugins)
    deregister_loader_plugin_path(LOAD_PATH)
    log.info("Global plug-ins unregistred")
