# -*- coding: utf-8 -*-
"""Pipeline tools for OpenPype Houdini integration."""
import os
import logging
from operator import attrgetter

import json

from openpype.host import HostBase, IWorkfileHost, ILoadHost, IPublishHost
import pyblish.api
from openpype.pipeline import (
    register_creator_plugin_path,
    register_loader_plugin_path,
    AVALON_CONTAINER_ID,
)
from openpype.hosts.max.api.menu import OpenPypeMenu
from openpype.hosts.max.api import lib
from openpype.hosts.max.api.plugin import MS_CUSTOM_ATTRIB
from openpype.hosts.max import MAX_HOST_DIR

from pymxs import runtime as rt  # noqa

log = logging.getLogger("openpype.hosts.max")

PLUGINS_DIR = os.path.join(MAX_HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


class MaxHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):

    name = "max"
    menu = None

    def __init__(self):
        super(MaxHost, self).__init__()
        self._op_events = {}
        self._has_been_setup = False

    def install(self):
        pyblish.api.register_host("max")

        pyblish.api.register_plugin_path(PUBLISH_PATH)
        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)

        # self._register_callbacks()
        self.menu = OpenPypeMenu()

        self._has_been_setup = True

        def context_setting():
            return lib.set_context_setting()

        rt.callbacks.addScript(rt.Name('systemPostNew'),
                               context_setting)

    def has_unsaved_changes(self):
        # TODO: how to get it from 3dsmax?
        return True

    def get_workfile_extensions(self):
        return [".max"]

    def save_workfile(self, dst_path=None):
        rt.saveMaxFile(dst_path)
        return dst_path

    def open_workfile(self, filepath):
        rt.checkForSave()
        rt.loadMaxFile(filepath)
        return filepath

    def get_current_workfile(self):
        return os.path.join(rt.maxFilePath, rt.maxFileName)

    def get_containers(self):
        return ls()

    def _register_callbacks(self):
        rt.callbacks.removeScripts(id=rt.name("OpenPypeCallbacks"))

        rt.callbacks.addScript(
            rt.Name("postLoadingMenus"),
            self._deferred_menu_creation, id=rt.Name('OpenPypeCallbacks'))

    def _deferred_menu_creation(self):
        self.log.info("Building menu ...")
        self.menu = OpenPypeMenu()

    @staticmethod
    def create_context_node():
        """Helper for creating context holding node."""

        root_scene = rt.rootScene

        create_attr_script = ("""
attributes "OpenPypeContext"
(
    parameters main rollout:params
    (
        context type: #string
    )

    rollout params "OpenPype Parameters"
    (
        editText editTextContext "Context" type: #string
    )
)
        """)

        attr = rt.execute(create_attr_script)
        rt.custAttributes.add(root_scene, attr)

        return root_scene.OpenPypeContext.context

    def update_context_data(self, data, changes):
        try:
            _ = rt.rootScene.OpenPypeContext.context
        except AttributeError:
            # context node doesn't exists
            self.create_context_node()

        rt.rootScene.OpenPypeContext.context = json.dumps(data)

    def get_context_data(self):
        try:
            context = rt.rootScene.OpenPypeContext.context
        except AttributeError:
            # context node doesn't exists
            context = self.create_context_node()
        if not context:
            context = "{}"
        return json.loads(context)

    def save_file(self, dst_path=None):
        # Force forwards slashes to avoid segfault
        dst_path = dst_path.replace("\\", "/")
        rt.saveMaxFile(dst_path)


def ls() -> list:
    """Get all OpenPype instances."""
    objs = rt.objects
    containers = [
        obj for obj in objs
        if rt.getUserProp(obj, "id") == AVALON_CONTAINER_ID
    ]

    for container in sorted(containers, key=attrgetter("name")):
        yield lib.read(container)


def containerise(name: str, nodes: list, context, loader=None, suffix="_CON"):
    data = {
        "schema": "openpype:container-2.0",
        "id": AVALON_CONTAINER_ID,
        "name": name,
        "namespace": "",
        "loader": loader,
        "representation": context["representation"]["_id"],
    }

    container_name = f"{name}{suffix}"
    container = rt.container(name=container_name)
    for node in nodes:
        node.Parent = container

    if not lib.imprint(container_name, data):
        print(f"imprinting of {container_name} failed.")
    return container


def loadOpenpypeData():
    return rt.Execute(MS_CUSTOM_ATTRIB)
