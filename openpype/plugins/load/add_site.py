from openpype.client import get_linked_representation_id
from openpype.modules import ModulesManager
from openpype.pipeline import load
from openpype.modules.sync_server.utils import SiteAlreadyPresentError
from openpype.client.entities import (
    get_hero_version_by_subset_id,
    get_representation_by_id,
    get_version_by_id,
    get_representation_by_name
)


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
        # self.log wont propagate
        print("Adding {} to representation: {}".format(
              data["site_name"], data["_id"]))
        family = context["representation"]["context"]["family"]
        project_name = data["project_name"]
        repre_id = data["_id"]
        site_name = data["site_name"]

        representation_ids = self._add_hero_representation_ids(project_name,
                                                               repre_id)

        for repre_id in representation_ids:
            self.sync_server.add_site(project_name, repre_id, site_name,
                                      force=True)

        if family == "workfile":
            links = get_linked_representation_id(
                project_name,
                repre_id=repre_id,
                link_type="reference"
            )
            for link_repre_id in links:
                try:
                    representation_ids = self._add_hero_representation_ids(
                        project_name, link_repre_id)
                    for repre_id in representation_ids:
                        self.sync_server.add_site(project_name, repre_id,
                                                  site_name,
                                                  force=False)
                except SiteAlreadyPresentError:
                    # do not add/reset working site for references
                    self.log.debug("Site present", exc_info=True)

        self.log.debug("Site added.")

    def filepath_from_context(self, context):
        """No real file loading"""
        return ""

    def _add_hero_representation_ids(self, project_name, repre_id):
        """Find hero version if exists for repre_id.

        Args:
            project_name (str)
            repre_id (ObjectId)
        Returns:
            (list): at least [repre_id] if no hero version found
        """
        representation_ids = [repre_id]

        repre_doc = get_representation_by_id(
            project_name, repre_id, fields=["_id", "parent", "name"]
        )

        version_doc = get_version_by_id(project_name, repre_doc["parent"])
        if version_doc["type"] != "hero_version":
            hero_version = get_hero_version_by_subset_id(
                project_name, version_doc["parent"],
                fields=["_id", "version_id"]
            )
            if (hero_version and
                    hero_version["version_id"] == version_doc["_id"]):
                hero_repre_doc = get_representation_by_name(
                    project_name,
                    repre_doc["name"],
                    hero_version["_id"]
                )
                representation_ids.append(hero_repre_doc["_id"])

        return representation_ids
