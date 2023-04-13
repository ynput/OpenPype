# -*- coding: utf-8 -*-
import contextlib
import os
from collections import OrderedDict

import pyblish
import rv

from openpype.host import HostBase, ILoadHost, IWorkfileHost
from openpype.hosts.openrv import OPENRV_ROOT_DIR
from openpype.pipeline import (
    register_loader_plugin_path,
    register_inventory_action_path,
    register_creator_plugin_path,
    AVALON_CONTAINER_ID,
)
from . import lib

PLUGINS_DIR = os.path.join(OPENRV_ROOT_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")

OPENPYPE_ATTR_PREFIX = "openpype"


class OpenRVHost(HostBase, IWorkfileHost, ILoadHost):
    name = "openrv"

    def __init__(self):
        super(OpenRVHost, self).__init__()
        self._op_events = {}

    def install(self):
        pyblish.api.register_plugin_path(PUBLISH_PATH)
        pyblish.api.register_host("openrv")

        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)
        register_inventory_action_path(INVENTORY_PATH)

    def open_workfile(self, filepath):
        return rv.commands.addSources([filepath])

    def save_workfile(self, filepath=None):
        return rv.commands.saveSession(filepath)

    def work_root(self, session):
        work_dir = session.get("AVALON_WORKDIR")
        scene_dir = session.get("AVALON_SCENEDIR")
        if scene_dir:
            return os.path.join(work_dir, scene_dir)
        else:
            return work_dir

    def get_current_workfile(self):
        return rv.commands.sessionFileName()

    def workfile_has_unsaved_changes(self):
        # dont ask to save if we are on the startup scene without a name
        # set to untitled project and return False
        print("filename", rv.commands.sessionFileName())
        return False

    def get_workfile_extensions(self):
        return [".rv"]

    def get_containers(self):
        """Get containers.
        """
        all_items = gather_containers()
        for rvnode in all_items:
            parsed = parse_container(rvnode)
            yield parsed

    @contextlib.contextmanager
    def maintained_selection(self):
        with lib.maintained_selection():
            yield


def imprint(node, data):
    """Store string attributes with value on a node

    Args:
        node (object): The node to imprint data on.
        data (dict): Key value pairs of attributes to create.
        group (str): The Group to add the attributes to.

    Returns:
        None

    """
    for attr, value in data.items():
        # Create and set the attribute
        prop = "{}.{}.{}".format(node, OPENPYPE_ATTR_PREFIX, attr)
        if not rv.commands.propertyExists(prop):
            rv.commands.newProperty(prop, rv.commands.StringType, 1)
        rv.commands.setStringProperty(prop, [str(value)], True)

    return


def imprint_container(node, name, namespace, context, loader):
    """Imprint `node` with container metadata.

    Arguments:
        node (object): The node to containerise.
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        context (dict): Asset information
        loader (str): Name of loader used to produce this container.

    Returns:
        None

    """

    data = [
        ("schema", "openpype:container-2.0"),
        ("id", AVALON_CONTAINER_ID),
        ("name", name),
        ("namespace", namespace),
        ("loader", loader),
        ("representation", context["representation"]["_id"])
    ]

    # We use an OrderedDict to make sure the attributes
    # are always created in the same order. This is solely
    # to make debugging easier when reading the values in
    # the attribute editor.
    imprint(node, OrderedDict(data))


def parse_container(node):
    """Returns imprinted container data of a tool

    This reads the imprinted data from `imprint_container`.

    """
    # If not all required data return None
    required = ['id', 'schema', 'name',
                'namespace', 'loader', 'representation']

    data = {}
    for key in required:
        attr = node + "." + OPENPYPE_ATTR_PREFIX + "." + key
        if not rv.commands.propertyExists(attr):
            return

        value = rv.commands.getStringProperty(attr)[0]
        data[key] = value

    # Store the node's name
    data["objectName"] = str(node)

    # Store reference to the node object
    data["node"] = node

    return data


def gather_containers():
    """gathers all rv nodes list
    """
    all_files = []
    all_nodes = rv.commands.nodes()
    for node in all_nodes:
        prop = node + "." + OPENPYPE_ATTR_PREFIX + ".schema"
        if rv.commands.propertyExists(prop):
            all_files.append(node)
    return set(all_files)


def get_containers():
    """Get containers.
    """
    all_items = gather_containers()
    for rvnode in all_items:
        parsed = parse_container(rvnode)
        yield parsed


@contextlib.contextmanager
def openrv_project_file_lock_and_undo_chunk(openrv_project_file,
                                            undo_queue_name="Script CMD"):
    """Lock rv session and open an undo chunk during the context"""
    pass
