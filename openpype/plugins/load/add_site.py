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
        self.add_site_to_representation(project_name,
                                        repre_id,
                                        data["site_name"],
                                        is_main=True)

        if family == "workfile":
            links = get_linked_ids_for_representations(project_name,
                                                       add_ids,
                                                       link_type="reference")
            for link_repre_id in links:
                self.add_site_to_representation(project_name,
                                                link_repre_id,
                                                data["site_name"],
                                                is_main=False)

        self.log.debug("Site added.")

    def add_site_to_representation(self, project_name, representation_id,
                                   site_name, is_main):
        """Adds new site to representation_id, resets if exists

        Args:
            project_name (str)
            representation_id (ObjectId):
            site_name (str)
            is_main (bool): true for really downloaded, false for references,
                force redownload main file always, for references only if
                broken
        """
        try:
            self.sync_server.add_site(project_name, representation_id,
                                      site_name,
                                      force=is_main,
                                      force_only_broken=not is_main)
        except SiteAlreadyPresentError:
            self.log.debug("Site present", exc_info=True)

    def filepath_from_context(self, context):
        """No real file loading"""
        return ""
