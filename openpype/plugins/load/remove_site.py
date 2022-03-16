from openpype.modules import ModulesManager
from openpype.pipeline import load


class RemoveSyncSite(load.LoaderPlugin):
    """Remove sync site and its files on representation"""
    representations = ["*"]
    families = ["*"]

    label = "Remove Sync Site"
    order = 4
    icon = "download"
    color = "#999999"

    def load(self, context, name=None, namespace=None, data=None):
        self.log.info("Removing {} on representation: {}".format(
            data["site_name"], data["_id"]))
        self.remove_site_on_representation(data["project_name"],
                                           data["_id"],
                                           data["site_name"])
        self.log.debug("Site added.")

    @staticmethod
    def remove_site_on_representation(project_name, representation_id,
                                      site_name):
        manager = ModulesManager()
        sync_server = manager.modules_by_name["sync_server"]
        sync_server.remove_site(project_name, representation_id,
                                site_name, True)

    def filepath_from_context(self, context):
        """No real file loading"""
        return ""
