import os
import errno
import logging
import contextlib


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
        return 

    def save_workfile(self, filepath=None):
        return 

    def work_root(self, session):
        return 

    def get_current_workfile(self):
        return 

    def workfile_has_unsaved_changes(self):
        return 

    def get_workfile_extensions(self):
        return 

    def get_containers(self):
        return 

    @contextlib.contextmanager
    def maintained_selection(self):
        for x in []:
            yield

def uninstall():
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    pyblish.api.deregister_host("commandline")
    pyblish.api.deregister_host("c4dpy")
    pyblish.api.deregister_host("cinema4d")

    deregister_loader_plugin_path(LOAD_PATH)
    deregister_creator_plugin_path(CREATE_PATH)
    deregister_inventory_action_path(INVENTORY_PATH)

    #menu.uninstall()