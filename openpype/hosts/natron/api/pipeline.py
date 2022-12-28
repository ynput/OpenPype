# -*- coding: utf-8 -*-
"""Pipeline tools for OpenPype Gaffer integration."""
import os
import logging

from openpype.host import HostBase, IWorkfileHost, ILoadHost, IPublishHost

import pyblish.api

from openpype.pipeline import (
    register_creator_plugin_path,
    register_loader_plugin_path,
    AVALON_CONTAINER_ID
)
from openpype.hosts.natron import NATRON_HOST_DIR

log = logging.getLogger("openpype.hosts.natron")

PLUGINS_DIR = os.path.join(NATRON_HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


def get_app():
    """Return first available Natron app instance?"""
    # TODO: Implement
    return None


class NatronHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    name = "natron"

    def __init__(self):
        super(NatronHost, self).__init__()
        self._has_been_setup = False

    def install(self):
        pyblish.api.register_host("natron")

        pyblish.api.register_plugin_path(PUBLISH_PATH)
        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)

        log.info("Installing callbacks ... ")
        # register_event_callback("init", on_init)
        # self._register_callbacks()
        # register_event_callback("before.save", before_save)
        # register_event_callback("save", on_save)
        # register_event_callback("open", on_open)
        # register_event_callback("new", on_new)

        # pyblish.api.register_callback(
        #     "instanceToggled", on_pyblish_instance_toggled
        # )

        self._has_been_setup = True

    def has_unsaved_changes(self):
        # TODO: Implement
        return False

    def get_workfile_extensions(self):
        return [".ntp"]

    def save_workfile(self, dst_path=None):
        if not dst_path:
            dst_path = self.get_current_workfile()

        app = get_app()
        return app.saveProjectAs(dst_path)

    def open_workfile(self, filepath):

        if not os.path.exists(filepath):
            raise RuntimeError("File does not exist: {}".format(filepath))

        app = get_app()
        app.loadProject(filepath)
        return filepath

    def get_current_workfile(self):
        app = get_app()
        return app.getProjectParam("projectPath").getValue()

    def get_containers(self):
        return []

    @staticmethod
    def create_context_node():
        pass

    def update_context_data(self, data, changes):
        pass

    def get_context_data(self):
        pass


def imprint_container(node,
                      name,
                      namespace,
                      context,
                      loader=None):
    """Imprint a Loader with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        tool (object): The node in Fusion to imprint as container, usually a
            Loader.
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        context (dict): Asset information
        loader (str, optional): Name of loader used to produce this container.

    Returns:
        None

    """

    data = [
        ("schema", "openpype:container-2.0"),
        ("id", AVALON_CONTAINER_ID),
        ("name", str(name)),
        ("namespace", str(namespace)),
        ("loader", str(loader)),
        ("representation", str(context["representation"]["_id"])),
    ]

    imprint(node, data)


def imprint(node, data, section="OpenPype"):
    # TODO: Implement
    pass
