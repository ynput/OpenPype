# -*- coding: utf-8 -*-
"""Pipeline tools for OpenPype Gaffer integration."""
import os
import sys
import json
import logging

import Gaffer  # noqa

from openpype.host import HostBase, IWorkfileHost, ILoadHost, IPublishHost

import pyblish.api

from openpype.pipeline import (
    register_creator_plugin_path,
    register_loader_plugin_path,
    AVALON_CONTAINER_ID
)
from openpype.hosts.gaffer import GAFFER_HOST_DIR

log = logging.getLogger("openpype.hosts.gaffer")

PLUGINS_DIR = os.path.join(GAFFER_HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")

self = sys.modules[__name__]
self.root = None

JSON_PREFIX = "JSON:::"


def set_root(root):
    self.root = root


def get_root():
    return self.root


class GafferHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    name = "gaffer"

    _context_plug = "openpype_context"

    def __init__(self):
        super(GafferHost, self).__init__()
        self._has_been_setup = False

    def install(self):
        pyblish.api.register_host("gaffer")

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
        script = get_root()
        return script["unsavedChanges"].getValue()

    def get_workfile_extensions(self):
        return [".gfr"]

    def save_workfile(self, dst_path=None):
        if not dst_path:
            dst_path = self.get_current_workfile()

        dst_path = dst_path.replace("\\", "/")

        script = get_root()
        script.serialiseToFile(dst_path)
        script["fileName"].setValue(dst_path)
        script["unsavedChanges"].setValue(False)

        application = script.ancestor(Gaffer.ApplicationRoot)
        if application:
            import GafferUI.FileMenu
            GafferUI.FileMenu.addRecentFile(application, dst_path)

        return dst_path

    def open_workfile(self, filepath):

        if not os.path.exists(filepath):
            raise RuntimeError("File does not exist: {}".format(filepath))

        script = get_root()
        if script:
            script["fileName"].setValue(filepath)
            script.load()
        return filepath

    def get_current_workfile(self):
        script = get_root()
        return script["fileName"].getValue()

    def get_containers(self):
        script = get_root()

        required = [
            "schema", "id", "name", "namespace", "representation", "loader"
        ]

        for node in script.children(Gaffer.Node):
            if "user" not in node:
                # No user attributes
                continue

            user = node["user"]
            if any(key not in user for key in required):
                continue

            if user["id"].getValue() != AVALON_CONTAINER_ID:
                continue
            container = {
                key: user[key].getValue() for key in required
            }
            container["objectName"] = node.fullName()
            container["_node"] = node

            yield container

    def update_context_data(self, data, changes):
        """Store context data as single JSON blob in script's user data"""
        script = get_root()
        data_str = json.dumps(data)

        # Always override the full plug - even if it already exists
        script["user"][self._context_plug] = Gaffer.StringPlug(
            defaultValue=data_str,
            flags=Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic
        )

    def get_context_data(self):
        script = get_root()
        if "user" in script and self._context_plug in script["user"]:
            data_str = script["user"][self._context_plug].getValue()
            return json.loads(data_str)
        return {}


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


def imprint(node: Gaffer.Node,
            data: dict,
            section: str = "OpenPype"):
    """Store and persist data on a node as `user` data.

    Args:
        node (Gaffer.Node): The node to store the data on.
            This can also be the workfile's root script node.
        data (dict): The key, values to store.
            Any `dict` values will be treated as JSON data and stored as
            string with `JSON:::` as a prefix to the value.
        section (str): Used to register the plug into a subsection in
            the user data allowing them to group data together.

    Returns:

    """

    FLAGS = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic

    for key, value in data:
        # Dict to JSON
        if isinstance(value, dict):
            value = json.dumps(value)
            value = f"{JSON_PREFIX}{value}"

        if key in node["user"]:
            # Set existing attribute
            try:
                node["user"][key].setValue(value)
                continue
            except Exception:
                # If an exception occurs then we'll just replace the key
                # with a new plug (likely types have changed)
                log.warning("Unable to set %s attribute %s to value %s (%s). "
                            "Likely there is a value type mismatch. "
                            "Plug will be replaced.",
                            node.getName(), key, value, type(value),
                            exc_info=sys.exc_info())
                pass

        # Generate new plug with value as default value
        if isinstance(value, str):
            plug = Gaffer.StringPlug(key, defaultValue=value, flags=FLAGS)
        elif isinstance(value, bool):
            plug = Gaffer.BoolPlug(key, defaultValue=value, flags=FLAGS)
        elif isinstance(value, float):
            plug = Gaffer.FloatPlug(key, defaultValue=value, flags=FLAGS)
        elif isinstance(value, int):
            plug = Gaffer.IntPlug(key, defaultValue=value, flags=FLAGS)
        else:
            raise TypeError(
                f"Unsupported value type: {type(value)} -> {value}"
            )

        if section:
            Gaffer.Metadata.registerValue(plug, "layout:section", section)

        node["user"][key] = plug
