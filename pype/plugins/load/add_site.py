from avalon import api
from pype.modules import ModulesManager


class AddSyncSite(api.Loader):
    """Add sync site to representation"""
    representations = ["*"]
    families = ["*"]

    label = "Add Sync Site"
    order = 20
    icon = "download"
    color = "#999999"

    def load(self, context, name=None, namespace=None, data=None):
        self.log.info("Adding site to representation: {0}".format(self.fname))
        self.add_site_to_representation(data["project_name"],
                                        data["_id"],
                                        data["site_name"])

    @staticmethod
    def add_site_to_representation(project_name, representation_id, site_name):
        manager = ModulesManager()
        sync_server = manager.modules_by_name["sync_server"]
        sync_server.add_site(project_name, representation_id, site_name)

    def filepath_from_context(self, context):
        """No real file loading"""
        return ""
