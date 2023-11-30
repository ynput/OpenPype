from collections import defaultdict

from openpype.lib import Logger
from openpype.client.entities import get_representations
from openpype.client import get_linked_representation_id
from openpype.tools.ayon_loader.abstract import ActionItem
from openpype.modules import ModulesManager

from openpype.modules.sync_server.utils import SiteAlreadyPresentError
from openpype.tools.ayon_utils.models import NestedCacheItem

DOWNLOAD_IDENTIFIER = "sitesync.download"
UPLOAD_IDENTIFIER = "sitesync.upload"
REMOVE_IDENTIFIER = "sitesync.remove"

log = Logger.get_logger(__name__)


def _default_version_availability():
    return 0, 0


def _default_repre_status():
    return 0.0, 0.0

class SiteSyncModel:
    status_lifetime = 20

    def __init__(self, controller):
        self._controller = controller

        self._site_sync_enabled_cache = NestedCacheItem(
            levels=1, lifetime=self.lifetime
        )
        self._version_availability_cache = NestedCacheItem(
            levels=2,
            default_factory=_default_version_availability,
            lifetime=self.status_lifetime
        )
        self._repre_status_cache = NestedCacheItem(
            levels=2,
            default_factory=_default_repre_status,
            lifetime=self.status_lifetime
        )
        manager = ModulesManager()
        self._sitesync_addon = manager.modules_by_name.get("sync_server")

    def reset(self):
        self._site_sync_enabled_cache.reset()
        self._version_availability_cache.reset()
        self._repre_status_cache.reset()

    def is_site_sync_enabled(self, project_name=None):
        """Site sync is enabled for a project.

        Returns false if site sync addon is not available or enabled
            or project has disabled it.

        Args:
            project_name (Union[str, None]): Project name. If project name
                is 'None', True is returned if site sync addon
                is available and enabled.

        Returns:
            bool: Site sync is enabled.
        """

        if not self._is_site_sync_addon_enabled():
            return False
        cache = self._site_sync_enabled_cache[project_name]
        if not cache.is_valid:
            enabled = True
            if project_name:
                enabled = self._sitesync_addon.is_project_enabled(
                    project_name, single=True
                )
            cache.update_data(enabled)
        return cache.get_data()
    # TODO cache
    def get_site_icons(self):
        return self._sitesync_addon.get_site_icons()

    # TODO cache
    def get_active_site(self, project_name):
        if not project_name:
            return
        return self._sitesync_addon.get_active_site(project_name)

    # TODO cache
    def get_remote_site(self, project_name):
        if not project_name:
            return
        return self._sitesync_addon.get_remote_site(project_name)

    def get_active_site_icon_def(self, project_name):
        if not project_name:
            return
        provider = self._sitesync_addon.get_provider_for_site(project_name,
            self.get_active_site(project_name))
        return self.get_site_icons().get(provider)

    def get_remote_site_icon_def(self, project_name):
        if not project_name:
            return
        provider = self._sitesync_addon.get_provider_for_site(
            project_name,
            self.get_remote_site(project_name)
        )
        return self.get_site_icons().get(provider)

    def get_version_sync_availability(self, project_name, version_ids):
        """Returns how many representations are available on sites.

        Returned value `{version_id: (4, 6)}` denotes that locally are
            available 4 and remotely 6 representation.
        NOTE: Available means they were synced to site.

        Returns:
            dict[str, tuple[int, int]]
        """

        if not self.is_site_sync_enabled(project_name):
            return {
                version_id: _default_version_availability()
                for version_id in version_ids
            }

        output = {}
        project_cache = self._version_availability_cache[project_name]
        invalid_ids = set()
        for version_id in version_ids:
            repre_cache = project_cache[version_id]
            if repre_cache.is_valid:
                output[version_id] = repre_cache.get_data()
            else:
                invalid_ids.add(version_id)

        if invalid_ids:
            self._refresh_version_availability(
                project_name, invalid_ids
            )
            for version_id in invalid_ids:
                version_cache = project_cache[version_id]
                output[version_id] = version_cache.get_data()
        return output

    def get_representations_sync_status(
        self, project_name, representation_ids
    ):
        """

        Args:
            project_name (str): Project name.
            representation_ids (Iterable[str]): Representation ids.

        Returns:
            dict[str, tuple[float, float]]
        """

        if not self.is_site_sync_enabled(project_name):
            return {
                repre_id: _default_repre_status()
                for repre_id in representation_ids
            }

        output = {}
        project_cache = self._repre_status_cache[project_name]
        invalid_ids = set()
        for repre_id in representation_ids:
            repre_cache = project_cache[repre_id]
            if repre_cache.is_valid:
                output[repre_id] = repre_cache.get_data()
            else:
                invalid_ids.add(repre_id)

        if invalid_ids:
            self._refresh_representations_sync_status(
                project_name, invalid_ids
            )
            for repre_id in invalid_ids:
                repre_cache = project_cache[repre_id]
                output[repre_id] = repre_cache.get_data()
        return output

    def get_sitesync_action_items(self, project_name, representation_ids):
        if not self.is_site_sync_enabled(project_name):
            return []
        repres_status = self.get_representations_sync_state(project_name,
                                                            representation_ids)

        action_items = []
        repre_ids_per_identifier = defaultdict(list)

        for repre_id in representation_ids:
            repre_status = repres_status[repre_id]
            local_status, remote_status = repre_status

            if local_status:
                repre_ids_per_identifier[UPLOAD_IDENTIFIER].append(repre_id)
                repre_ids_per_identifier[REMOVE_IDENTIFIER].append(repre_id)
            if remote_status:
                repre_ids_per_identifier[DOWNLOAD_IDENTIFIER].append(repre_id)

        for identifier, repre_ids in repre_ids_per_identifier.items():
            if identifier == DOWNLOAD_IDENTIFIER:
                action_items.append(self._create_download_action_item(
                    project_name, repre_ids))
            if identifier == UPLOAD_IDENTIFIER:
                action_items.append(self._create_upload_action_item(
                    project_name, repre_ids))
            if identifier == REMOVE_IDENTIFIER:
                action_items.append(self._create_delete_action_item(
                    project_name, repre_ids))

        return action_items

    def _is_site_sync_addon_enabled(self):
        """
        Returns:
            bool: Site sync addon is enabled.
        """

        if self._sitesync_addon is None:
            return False
        return self._sitesync_addon.enabled

    def _refresh_version_availability(self, project_name, version_ids):
        if not project_name or not version_ids:
            return
        project_cache = self._version_availability_cache[project_name]

        avail_by_id = self._sitesync_addon.get_version_sync_availability(
            project_name,
            version_ids,
            self.get_active_site(project_name),
            self.get_remote_site(project_name),
        )
        for version_id in version_ids:
            status = avail_by_id.get(version_id)
            if status is None:
                status = _default_version_availability()
            project_cache[version_id].update_data(status)

    def _refresh_representations_sync_status(
        self, project_name, representation_ids
    ):
        if not project_name or not representation_ids:
            return
        project_cache = self._repre_status_cache[project_name]
        status_by_repre_id = self._sitesync_addon.get_representations_sync_status(
            project_name,
            representation_ids,
            self.get_active_site(project_name),
            self.get_remote_site(project_name),
        )
        for repre_id in representation_ids:
            status = status_by_repre_id.get(repre_id)
            if status is None:
                status = _default_repre_status()
            project_cache[repre_id].update_data(status)

    def _create_download_action_item(self, project_name, representation_ids):
        return self._create_action_item(
            project_name,
            representation_ids,
            DOWNLOAD_IDENTIFIER,
            "Download",
            "Mark representation for download locally",
            "download"
        )

    def _create_upload_action_item(self, project_name, representation_ids):
        return self._create_action_item(
            project_name,
            representation_ids,
            UPLOAD_IDENTIFIER,
            "Upload",
            "Mark representation for upload remotely",
            "upload"
        )

    def _create_delete_action_item(self, project_name, representation_ids):
        return self._create_action_item(project_name,
                                        representation_ids,
                                        REMOVE_IDENTIFIER,
                                        "Remove from local",
                                        "Remove local synchronization",
                                        "trash")

    def _create_action_item(self, project_name, representation_ids,
                            identifier, label, tooltip, icon_name):
        icon_name = f"fa.{icon_name}"
        return ActionItem(
            identifier,
            label,
            icon={"type": "awesome-font", "name": icon_name,
                  "color": "#999999"},
            tooltip=tooltip,
            options={},
            order=1,
            project_name=project_name,
            folder_ids=[],
            product_ids=[],
            version_ids=[],
            representation_ids=representation_ids,
        )

    def is_sitesync_action(self, identifier):
        """Should be `identifier` handled by SiteSync."""
        return identifier in {UPLOAD_IDENTIFIER,
                              DOWNLOAD_IDENTIFIER,
                              REMOVE_IDENTIFIER}

    def trigger_action_item(
        self,
        identifier,
        project_name,
        representation_ids
    ):
        """Resets status for site_name or remove local files."""
        active_site = self.get_active_site(project_name)
        remote_site = self.get_remote_site(project_name)

        repre_docs = list(get_representations(
            project_name, representation_ids=representation_ids
        ))
        families_per_repre_id = {item["_id"]: item["context"]["family"]
                                 for item in repre_docs}

        for repre_id in representation_ids:
            if identifier == DOWNLOAD_IDENTIFIER:
                self._add_site(project_name, repre_id,
                               active_site,
                               families_per_repre_id[repre_id])
            if identifier == UPLOAD_IDENTIFIER:
                self._add_site(project_name, repre_id,
                               remote_site,
                               families_per_repre_id[repre_id])

            if identifier == REMOVE_IDENTIFIER:
                self._sitesync_addon.remove_site(project_name,
                                                 repre_id,
                                                 active_site,
                                                 remove_local_files=True)

    def _add_site(self, project_name, repre_id, site_name,
                  family):
        self._sitesync_addon.add_site(project_name,
                                      repre_id,
                                      site_name,
                                      force=True)
        if family == "workfile":
            links = get_linked_representation_id(
                project_name,
                repre_id=repre_id,
                link_type="reference"
            )
            for link_repre_id in links:
                try:
                    print("Adding {} to linked representation: {}".format(
                        site_name, link_repre_id))
                    self.sync_server.add_site(project_name, link_repre_id,
                                              site_name,
                                              force=False)
                except SiteAlreadyPresentError:
                    # do not add/reset working site for references
                    log.debug("Site present", exc_info=True)
