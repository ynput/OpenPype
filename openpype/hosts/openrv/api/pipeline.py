# -*- coding: utf-8 -*-
import os
import json
from collections import OrderedDict

import pyblish
import rv

from openpype.host import HostBase, ILoadHost, IWorkfileHost, IPublishHost
from openpype.hosts.openrv import OPENRV_ROOT_DIR
from openpype.pipeline import (
    register_loader_plugin_path,
    register_inventory_action_path,
    register_creator_plugin_path,
    AVALON_CONTAINER_ID,
)

PLUGINS_DIR = os.path.join(OPENRV_ROOT_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")

OPENPYPE_ATTR_PREFIX = "openpype."
JSON_PREFIX = "JSON:::"


class OpenRVHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
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
        filename = rv.commands.sessionFileName()
        if filename == "Untitled":
            return
        else:
            return filename

    def workfile_has_unsaved_changes(self):
        # RV has `State.unsavedChanges` attribute however that appears to
        # always return false and is never set to be true. As such, for now
        # we always return False.
        return False

    def get_workfile_extensions(self):
        return [".rv"]

    def get_containers(self):
        for container in get_containers():
            yield container

    def update_context_data(self, data, changes):
        imprint("root", data, prefix=OPENPYPE_ATTR_PREFIX)

    def get_context_data(self):
        return read("root", prefix=OPENPYPE_ATTR_PREFIX)


def imprint(node, data, prefix=None):
    """Store attributes with value on a node.

    Args:
        node (object): The node to imprint data on.
        data (dict): Key value pairs of attributes to create.
        prefix (str): A prefix to add to all keys in the data.

    Returns:
        None

    """
    node_prefix = f"{node}.{prefix}" if prefix else f"{node}."
    for attr, value in data.items():
        # Create and set the attribute
        prop = f"{node_prefix}.{attr}"

        if isinstance(value, (dict, list, tuple)):
            value = f"{JSON_PREFIX}{json.dumps(value)}"

        if isinstance(value, (bool, int)):
            type_name = "Int"
        elif isinstance(value, float):
            type_name = "Float"
        elif isinstance(value, str):
            type_name = "String"
        else:
            raise TypeError("Unsupport data type to imprint: "
                            "{} (type: {})".format(value, type(value)))

        if not rv.commands.propertyExists(prop):
            type_ = getattr(rv.commands, f"{type_name}Type")
            rv.commands.newProperty(prop, type_, 1)
        set_property = getattr(rv.commands, f"set{type_name}Property")
        set_property(prop, [value], True)


def read(node, prefix=None):
    """Read properties from the given node with the values

    This function assumes all read values are of a single width and will
    return only the first entry. As such, arrays or multidimensional properties
    will not be returned correctly.

    Args:
        node (str): Name of node.
        prefix (str, optional): A prefix for the attributes to consider.
            This prefix will be stripped from the output key.

    Returns:
        dict: The key, value of the properties.

    """
    properties = rv.commands.properties(node)
    node_prefix = f"{node}.{prefix}" if prefix else f"{node}."
    type_getters = {
        1: rv.commands.getFloatProperty,
        2: rv.commands.getIntProperty,
        # Not sure why 3, 4 and 5 don't seem to be types
        5: rv.commands.getHalfProperty,
        6: rv.commands.getByteProperty,
        8: rv.commands.getStringProperty
    }

    data = {}
    for prop in properties:
        if prefix is not None and not prop.startswith(node_prefix):
            continue

        info = rv.commands.propertyInfo(prop)
        type_num = info["type"]
        value = type_getters[type_num](prop)
        if value:
            value = value[0]
        else:
            value = None

        if type_num == 8 and value and value.strip().startswith(JSON_PREFIX):
            # String
            value = json.loads(value.strip()[len(JSON_PREFIX):])

        key = prop[len(node_prefix):]
        data[key] = value

    return data


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
        ("id", str(AVALON_CONTAINER_ID)),
        ("name", str(name)),
        ("namespace", str(namespace)),
        ("loader", str(loader)),
        ("representation", str(context["representation"]["_id"]))
    ]

    # We use an OrderedDict to make sure the attributes
    # are always created in the same order. This is solely
    # to make debugging easier when reading the values in
    # the attribute editor.
    imprint(node, OrderedDict(data), prefix=OPENPYPE_ATTR_PREFIX)


def parse_container(node):
    """Returns imprinted container data of a tool

    This reads the imprinted data from `imprint_container`.

    """
    # If not all required data return None
    required = ['id', 'schema', 'name',
                'namespace', 'loader', 'representation']

    data = {}
    for key in required:
        prop = f"{node}.{OPENPYPE_ATTR_PREFIX}{key}"
        if not rv.commands.propertyExists(prop):
            return

        value = rv.commands.getStringProperty(prop)[0]
        data[key] = value

    # Store the node's name
    data["objectName"] = str(node)

    # Store reference to the node object
    data["node"] = node

    return data


def get_container_nodes():
    """Return a list of node names that are marked as loaded container."""
    container_nodes = []
    for node in rv.commands.nodes():
        prop = f"{node}.{OPENPYPE_ATTR_PREFIX}schema"
        if rv.commands.propertyExists(prop):
            container_nodes.append(node)
    return container_nodes


def get_containers():
    """Yield container data for each container found in current workfile."""
    for node in get_container_nodes():
        container = parse_container(node)
        if container:
            yield container
