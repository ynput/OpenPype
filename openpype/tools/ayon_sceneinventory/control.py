import ayon_api

from openpype.lib.events import QueuedEventSystem
from openpype.host import ILoadHost
from openpype.pipeline import (
    registered_host,
    get_current_context,
)
from openpype.tools.ayon_utils.models import HierarchyModel

from .models import SiteSyncModel


class SceneInventoryController:
    """This is a temporary controller for AYON.

    Goal of this temporary controller is to provide a way to get current
    context instead of using 'AvalonMongoDB' object (or 'legacy_io').

    Also provides (hopefully) cleaner api for site sync.
    """

    def __init__(self, host=None):
        if host is None:
            host = registered_host()
        self._host = host
        self._current_context = None
        self._current_project = None
        self._current_folder_id = None
        self._current_folder_set = False

        self._site_sync_model = SiteSyncModel(self)
        # Switch dialog requirements
        self._hierarchy_model = HierarchyModel(self)
        self._event_system = self._create_event_system()

    def emit_event(self, topic, data=None, source=None):
        if data is None:
            data = {}
        self._event_system.emit(topic, data, source)

    def register_event_callback(self, topic, callback):
        self._event_system.add_callback(topic, callback)

    def reset(self):
        self._current_context = None
        self._current_project = None
        self._current_folder_id = None
        self._current_folder_set = False

        self._site_sync_model.reset()
        self._hierarchy_model.reset()

    def get_current_context(self):
        if self._current_context is None:
            if hasattr(self._host, "get_current_context"):
                self._current_context = self._host.get_current_context()
            else:
                self._current_context = get_current_context()
        return self._current_context

    def get_current_project_name(self):
        if self._current_project is None:
            self._current_project = self.get_current_context()["project_name"]
        return self._current_project

    def get_current_folder_id(self):
        if self._current_folder_set:
            return self._current_folder_id

        context = self.get_current_context()
        project_name = context["project_name"]
        folder_name = context.get("asset_name")
        folder_id = None
        if folder_name:
            folder = ayon_api.get_folder_by_path(project_name, folder_name)
            if folder:
                folder_id = folder["id"]

        self._current_folder_id = folder_id
        self._current_folder_set = True
        return self._current_folder_id

    def get_containers(self):
        host = self._host
        if isinstance(host, ILoadHost):
            return list(host.get_containers())
        elif hasattr(host, "ls"):
            return list(host.ls())
        return []

    # Site Sync methods
    def is_sync_server_enabled(self):
        return self._site_sync_model.is_sync_server_enabled()

    def get_sites_information(self):
        return self._site_sync_model.get_sites_information()

    def get_site_provider_icons(self):
        return self._site_sync_model.get_site_provider_icons()

    def get_representations_site_progress(self, representation_ids):
        return self._site_sync_model.get_representations_site_progress(
            representation_ids
        )

    def resync_representations(self, representation_ids, site_type):
        return self._site_sync_model.resync_representations(
            representation_ids, site_type
        )

    # Switch dialog methods
    def get_folder_items(self, project_name, sender=None):
        return self._hierarchy_model.get_folder_items(project_name, sender)

    def get_folder_label(self, folder_id):
        if not folder_id:
            return None
        project_name = self.get_current_project_name()
        folder_item = self._hierarchy_model.get_folder_item(
            project_name, folder_id)
        if folder_item is None:
            return None
        return folder_item.label

    def _create_event_system(self):
        return QueuedEventSystem()
