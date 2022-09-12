import os
import errno
import logging
import contextlib

import c4d

import pyblish.api

from openpype.settings import get_project_settings
from openpype.host import HostBase, IWorkfileHost, ILoadHost
import openpype.hosts.cinema4d
from openpype.pipeline import (
    legacy_io,
    register_loader_plugin_path,
    register_inventory_action_path,
    register_creator_plugin_path,
    deregister_loader_plugin_path,
    deregister_inventory_action_path,
    deregister_creator_plugin_path,
    AVALON_CONTAINER_ID,
)
from .workio import (
    open_file,
    save_file,
    file_extensions,
    has_unsaved_changes,
    work_root,
    current_file
)

from . import lib


log = logging.getLogger("openpype.hosts.cinema4d")

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.cinema4d.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")

AVALON_CONTAINERS = ":AVALON_CONTAINERS"


class Cinema4DHost(HostBase, IWorkfileHost, ILoadHost):
    name = "cinema4d"

    def __init__(self):
        super(Cinema4DHost, self).__init__()


    def install(self):
        project_settings = get_project_settings(os.getenv("AVALON_PROJECT"))
        # process path mapping
        #dirmap_processor = MayaDirmap("maya", project_settings)
        #dirmap_processor.process_dirmap()

        pyblish.api.register_plugin_path(PUBLISH_PATH)
        pyblish.api.register_host("commandline")
        pyblish.api.register_host("c4dpy")
        pyblish.api.register_host("cinema4d")

        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)
        register_inventory_action_path(INVENTORY_PATH)
        self.log.info(PUBLISH_PATH)

       
    def open_workfile(self, filepath):
        return open_file(filepath)

    def save_workfile(self, filepath=None):
        return save_file(filepath)

    def get_current_workfile(self):
        return current_file()

    def workfile_has_unsaved_changes(self):
        return has_unsaved_changes()

    def get_workfile_extensions(self):
        return file_extensions()

    def get_containers(self):
        return ls()

    @contextlib.contextmanager
    def maintained_selection(self):
        with lib.maintained_selection():
            yield

def parse_container(container):
    """Return the container node's full container data.

    Args:
        container (str): A container node name.

    Returns:
        dict: The container schema data for this container node.

    """
    data = lib.read(container)

    # Backwards compatibility pre-schemas for containers
    data["schema"] = data.get("schema", "openpype:container-1.0")

    # Append transient data
    data["objectName"] = container.GetName()

    return data

def ls(doc=None):
    ids = {AVALON_CONTAINER_ID}
    if not doc:
        doc = c4d.documents.GetActiveDocument()
    for obj in lib.walk_hierarchy(doc.GetFirstObject()):
        #print(obj.get("id"))
        if obj.get("id") in ids:
            yield obj


def containerise(name,
                 namespace,
                 nodes,
                 context,
                 loader=None,
                 suffix="CON"
                 ):
    """Bundle `nodes` into an assembly and imprint it with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        nodes (list): Long names of nodes to containerise
        context (dict): Asset information
        loader (str, optional): Name of loader used to produce this container.
        suffix (str, optional): Suffix of container, defaults to `_CON`.

    Returns:
        container (str): Name of container assembly

    """
    doc = nodes[0].GetDocument()

    container = c4d.BaseObject(c4d.Oselection)
    doc.InsertObject(container)
    container_attrs = lib.ObjectAttrs(container)
    container_attrs["SELECTIONOBJECT_LIST"] = nodes
    container.SetName("%s_%s_%s" % (namespace, name, suffix))

    data = [
        ("schema", "openpype:container-2.0"),
        ("id", AVALON_CONTAINER_ID),
        ("name", name),
        ("namespace", namespace),
        ("loader", str(loader)),
        ("representation", context["representation"]["_id"]),
    ]

    for key, value in data:
        if not value:
            continue

        container_attrs.add_attr(key, value, exists_ok=True)

    main_container = None
    for obj_path in lib.walk_hierarchy(doc.GetFirstObject()):
        if obj_path.re_match("*AVALON_CONTAINERS") and obj_path.obj.GetType() == c4d.Oselection:
            main_container = obj_path.obj
            break

    if not main_container:
        main_container = c4d.BaseObject(c4d.Oselection)
        doc.InsertObject(main_container)
        main_container.SetName("AVALON_CONTAINERS")
        layer = lib.add_update_layer("__containers__", doc=doc, data={"manager":False})
        lib.add_object_to_layer("__containers__", main_container)

    main_container[c4d.SELECTIONOBJECT_LIST].InsertObject(container)
    lib.add_object_to_layer("__containers__", container)
    c4d.EventAdd()
    return container

def uninstall():
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    pyblish.api.deregister_host("commandline")
    pyblish.api.deregister_host("c4dpy")
    pyblish.api.deregister_host("cinema4d")

    deregister_loader_plugin_path(LOAD_PATH)
    deregister_creator_plugin_path(CREATE_PATH)
    deregister_inventory_action_path(INVENTORY_PATH)

    #menu.uninstall()