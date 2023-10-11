import ayon_api

from openpype.host import ILoadHost
from openpype.pipeline import (
    registered_host,
    get_current_context,
)

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

        self._site_sync_model = SiteSyncModel()

    def reset(self):
        self._site_sync_model.reset()

        self._current_context = None
        self._current_project = None
        self._current_folder_id = None
        self._current_folder_set = False

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
        folder_path = context.get("folder_path")
        folder_name = context.get("asset")
        folder_id = None
        if folder_path:
            folder = ayon_api.get_folder_by_path(project_name, folder_path)
            if folder:
                folder_id = folder["id"]
        elif folder_name:
            for folder in ayon_api.get_folders(
                project_name, names=[folder_name]
            ):
                folder_id = folder["id"]
                break

        self._current_folder_id = folder_id
        self._current_folder_set = True
        return self._current_folder_id

    def get_containers(self):
        host = self._host
        if isinstance(host, ILoadHost):
            return host.get_containers()
        elif hasattr(host, "ls"):
            return host.ls()
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
