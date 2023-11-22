from openpype.modules import ModulesManager


class SiteSyncModel:
    def __init__(self, controller):
        self._controller = controller

        manager = ModulesManager()
        self._sync_module = manager.modules_by_name.get("sitesync")

    @property
    def sync_module(self):
        if not self._sync_module:
            manager = ModulesManager()
            self._sync_module = manager.modules_by_name.get("sync_server")

        return self._sync_module

    def reset(self):
        pass

    def refresh(self):
        pass

    def is_site_sync_enabled(self, project_name):
        return project_name in self.sync_module.get_enabled_projects()

    def get_site_icons(self):
        return self.sync_module.get_site_icons()

    def get_active_site(self, project_name):
        if not project_name:
            return
        return self.sync_module.get_active_site(project_name)

    def get_remote_site(self, project_name):
        if not project_name:
            return
        return self.sync_module.get_remote_site(project_name)

    def get_active_site_icon_def(self, project_name):
        if not project_name:
            return
        provider = self.sync_module.get_provider_for_site(project_name,
            self.get_active_site(project_name))
        return self.get_site_icons().get(provider)

    def get_remote_site_icon_def(self, project_name):
        if not project_name:
            return
        provider = self.sync_module.get_provider_for_site(project_name,
            self.get_remote_site(project_name))
        return self.get_site_icons().get(provider)

    def get_version_availability(self, project_name, version_ids):
        """ Returns how many representations are available on sites.

        Returned value `{version_id: (4, 6)}` denotes that locally are
        available 4 and remotely 6 representation.
        (Available means they were synced to site OK).
        Returns:
            dict[str, tuple[int, int]]
        """
        if not self.is_site_sync_enabled(project_name):
            return {
                version_id: (0, 0)
                for version_id in version_ids
            }

        version_avail = self.sync_module.get_version_availability(
            project_name,
            version_ids,
            self.get_active_site(project_name),
            self.get_remote_site(project_name),
        )
        return version_avail

    def get_representations_sync_state(self, project_name, representation_ids):
        """
        Returns:
            dict[str, tuple[float, float]]
        """
        return self.sync_module.get_representations_sync_state(
            project_name,
            representation_ids,
            self.get_active_site(project_name),
            self.get_remote_site(project_name),
        )

    def get_representations_sync_actions(self, project_name, representation_ids):
        """
        Returns:
            list[ActionItem]
        """
        return []
