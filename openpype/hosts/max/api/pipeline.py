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

        rt.callbacks.addScript(rt.Name('filePostOpen'),
                               lib.check_colorspace)

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


def containerise(name: str, nodes: list, context,
                 namespace=None, loader=None, suffix="_CON"):
    data = {
        "schema": "openpype:container-2.0",
        "id": AVALON_CONTAINER_ID,
        "name": name,
        "namespace": namespace or "",
        "loader": loader,
        "representation": context["representation"]["_id"],
    }
    container_name = f"{namespace}:{name}{suffix}"
    container = rt.container(name=container_name)
    import_custom_attribute_data(container, nodes)
    if not lib.imprint(container_name, data):
        print(f"imprinting of {container_name} failed.")
    return container


def load_custom_attribute_data():
    """Re-loading the Openpype/AYON custom parameter built by the creator

    Returns:
        attribute: re-loading the custom OP attributes set in Maxscript
    """
    return rt.Execute(MS_CUSTOM_ATTRIB)


def import_custom_attribute_data(container: str, selections: list):
    """Importing the Openpype/AYON custom parameter built by the creator

    Args:
        container (str): target container which adds custom attributes
        selections (list): nodes to be added into
        group in custom attributes
    """
    attrs = load_custom_attribute_data()
    modifier = rt.EmptyModifier()
    rt.addModifier(container, modifier)
    container.modifiers[0].name = "OP Data"
    rt.custAttributes.add(container.modifiers[0], attrs)
    node_list = []
    sel_list = []
    for i in selections:
        node_ref = rt.NodeTransformMonitor(node=i)
        node_list.append(node_ref)
        sel_list.append(str(i))

    # Setting the property
    rt.setProperty(
        container.modifiers[0].openPypeData,
        "all_handles", node_list)
    rt.setProperty(
        container.modifiers[0].openPypeData,
        "sel_list", sel_list)


def update_custom_attribute_data(container: str, selections: list):
    """Updating the Openpype/AYON custom parameter built by the creator

    Args:
        container (str): target container which adds custom attributes
        selections (list): nodes to be added into
        group in custom attributes
    """
    if container.modifiers[0].name == "OP Data":
        rt.deleteModifier(container, container.modifiers[0])
    import_custom_attribute_data(container, selections)


def get_previous_loaded_object(container: str):
    """Get previous loaded_object through the OP data

    Args:
        container (str): the container which stores the OP data

    Returns:
        node_list(list): list of nodes which are previously loaded
    """
    node_list = []
    sel_list = rt.getProperty(container.modifiers[0].openPypeData, "sel_list")
    for obj in rt.Objects:
        if str(obj) in sel_list:
            node_list.append(obj)
    return node_list
