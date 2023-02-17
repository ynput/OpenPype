from openpype.modules import ModulesManager
from openpype.pipeline import load


class RemoveSyncSite(load.LoaderPlugin):
    """Remove sync site and its files on representation.

    Removes files only on local site!
    """
    representations = ["*"]
    families = ["*"]

    label = "Remove Sync Site"
    order = 4
    icon = "download"
    color = "#999999"

    _sync_server = None
    is_remove_site_loader = True

    @property
    def sync_server(self):
        if not self._sync_server:
            manager = ModulesManager()
            self._sync_server = manager.modules_by_name["sync_server"]

        return self._sync_server

    def load(self, context, name=None, namespace=None, data=None):
        project_name = context["project"]["name"]
        repre_doc = context["representation"]
        repre_id = repre_doc["_id"]
        site_name = data["site_name"]

        print("Removing {} on representation: {}".format(site_name, repre_id))

        self.sync_server.remove_site(project_name,
                                     repre_id,
                                     site_name,
                                     True)
        self.log.debug("Site removed.")

    def filepath_from_context(self, context):
        """No real file loading"""
        return ""
