from openpype.modules import ModulesManager
from openpype.pipeline import load


class AddSyncSite(load.LoaderPlugin):
    """Add sync site to representation"""
    representations = ["*"]
    families = ["*"]

    label = "Add Sync Site"
    order = 2  # lower means better
    icon = "download"
    color = "#999999"

    def load(self, context, name=None, namespace=None, data=None):
        self.log.info("Adding {} to representation: {}".format(
            data["site_name"], data["_id"]))
        self.add_site_to_representation(data["project_name"],
                                        data["_id"],
                                        data["site_name"])
        self.log.debug("Site added.")

    @staticmethod
    def add_site_to_representation(project_name, representation_id, site_name):
        """Adds new site to representation_id, resets if exists"""
        manager = ModulesManager()
        sync_server = manager.modules_by_name["sync_server"]
        sync_server.add_site(project_name, representation_id, site_name,
                             force=True)

    def filepath_from_context(self, context):
        """No real file loading"""
        return ""
