import os
import json

import pyblish.api

from openpype.host import (
    HostBase,
    IWorkfileHost,
    ILoadHost,
    IPublishHost,
)

from openpype.pipeline import (
    register_loader_plugin_path,
    register_inventory_action_path,
    register_creator_plugin_path,
)
from openpype.hosts.mrv2 import MRV2_ROOT_DIR

from .workio import (
    open_file,
    save_file,
    file_extensions,
    has_unsaved_changes,
    work_root,
    current_file
)

from mrv2 import session


PLUGINS_DIR = os.path.join(MRV2_ROOT_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


class Mrv2Host(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    name = "mrv2"

    context_metadata_key = "ayon_context"

    def install(self):
        pyblish.api.register_plugin_path(PUBLISH_PATH)
        pyblish.api.register_host("mrv2")

        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)
        register_inventory_action_path(INVENTORY_PATH)

    def open_workfile(self, filepath):
        return open_file(filepath)

    def save_workfile(self, filepath=None):
        return save_file(filepath)

    def work_root(self, session):
        return work_root(session)

    def get_current_workfile(self):
        return current_file()

    def workfile_has_unsaved_changes(self):
        return has_unsaved_changes()

    def get_workfile_extensions(self):
        return file_extensions()

    def get_containers(self):
        return []

    def get_context_data(self):
        data = session.metadata(self.context_metadata_key)
        if data:
            return json.loads(data)
        return {}

    def update_context_data(self, data, changes):
        session.setMetadata(self.context_metadata_key, json.dumps(data))
