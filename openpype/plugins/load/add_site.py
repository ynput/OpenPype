from openpype.modules import ModulesManager
from openpype.pipeline import load
from openpype.lib.avalon_context import get_linked_ids_for_representations
from openpype.modules.sync_server.utils import SiteAlreadyPresentError


class AddSyncSite(load.LoaderPlugin):
    """Add sync site to representation

    If family of synced representation is 'workfile', it looks for all
    representations which are referenced (loaded) in workfile with content of
    'inputLinks'.
    It doesn't do any checks for site, most common use case is when artist is
    downloading workfile to his local site, but it might be helpful when
    artist is re-uploading broken representation on remote site also.
    """
    representations = ["*"]
    families = ["*"]

    label = "Add Sync Site"
    order = 2  # lower means better
    icon = "download"
    color = "#999999"

    _sync_server = None
    is_add_site_loader = True

    @property
    def sync_server(self):
        if not self._sync_server:
            manager = ModulesManager()
            self._sync_server = manager.modules_by_name["sync_server"]

        return self._sync_server

    def load(self, context, name=None, namespace=None, data=None):
        self.log.info("Adding {} to representation: {}".format(
            data["site_name"], data["_id"]))
        family = context["representation"]["context"]["family"]
        project_name = data["project_name"]
        repre_id = data["_id"]
        site_name = data["site_name"]

        self.sync_server.add_site(project_name, repre_id, site_name,
                                  force=True)

        if family == "workfile":
            links = get_linked_ids_for_representations(project_name,
                                                       [repre_id],
                                                       link_type="reference")
            for link_repre_id in links:
                try:
                    self.sync_server.add_site(project_name, link_repre_id,
                                              site_name,
                                              force=False)
                except SiteAlreadyPresentError:
                    # do not add/reset working site for references
                    self.log.debug("Site present", exc_info=True)

        self.log.debug("Site added.")

    def filepath_from_context(self, context):
        """No real file loading"""
        return ""
