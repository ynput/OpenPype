import webbrowser

from openpype.pipeline import LauncherAction
from openpype.modules import ModulesManager
from openpype.client import get_project, get_asset_by_name


class ShowInKitsu(LauncherAction):
    name = "showinkitsu"
    label = "Show in Kitsu"
    icon = "external-link-square"
    color = "#e0e1e1"
    order = 10

    @staticmethod
    def get_kitsu_module():
        return ModulesManager().modules_by_name.get("kitsu")

    def is_compatible(self, session):
        if not session.get("AVALON_PROJECT"):
            return False

        kitsu_module = self.get_kitsu_module()
        if not kitsu_module or not kitsu_module.enabled:
            return False

        return True

    def process(self, session, **kwargs):

        # Context inputs
        project_name = session["AVALON_PROJECT"]
        asset_name = session.get("AVALON_ASSET", None)
        task_name = session.get("AVALON_TASK", None)

        project = get_project(project_name=project_name,
                              fields=["data.zou_id"])
        if not project:
            raise RuntimeError(f"Project {project_name} not found.")

        project_zou_id = project["data"].get("zou_id")
        if not project_zou_id:
            raise RuntimeError(f"Project {project_name} has no "
                               f"connected ftrack id.")

        asset_zou_data = None
        task_zou_id = None
        if asset_name:
            asset_fields = ["data.zou.id", "data.zou.type"]
            if task_name:
                asset_fields.append(f"data.tasks.{task_name}.zou.id")

            asset = get_asset_by_name(project_name,
                                      asset_name=asset_name,
                                      fields=asset_fields)

            asset_zou_data = asset["data"].get("zou")
            if not asset_zou_data:
                raise RuntimeError(
                    f"No zou asset data for asset: {asset_name}"
                )

            if task_name:
                task_data = asset["tasks"][task_name]
                task_zou_data = task_data.get("zou", {})
                if not task_zou_data:
                    self.log.debug(f"No zou task data for task: {task_name}")
                task_zou_id = task_zou_data["id"]

        # Define URL
        url = self.get_url(project_id=project_zou_id,
                           asset_id=asset_zou_data["id"],
                           asset_type=asset_zou_data["type"],
                           task_id=task_zou_id)

        # Open URL in webbrowser
        self.log.info(f"Opening URL: {url}")
        webbrowser.open(url,
                        # Try in new tab
                        new=2)

    def get_url(self,
                project_id,
                asset_id=None,
                asset_type=None,
                task_id=None):

        kitsu_module = self.get_kitsu_module()

        # Get kitsu url with /api stripped
        kitsu_url = kitsu_module.server_url
        if kitsu_url.endswith("/api"):
            kitsu_url = kitsu_url[:-len("/api")]

        sub_url = f"/productions/{project_id}"
        asset_type_url = "assets" if asset_type == "Asset" else "shots"

        if task_id:
            # Go to task page
            # /productions/{project-id}/{asset_type}/tasks/{task_id}
            sub_url += f"/{asset_type_url}/tasks/{task_id}"

        elif asset_id:
            # Go to asset or shot page
            # /productions/{project-id}/assets/{entity_id}
            # /productions/{project-id}/shots/{entity_id}
            sub_url += f"/{asset_type_url}/{asset_id}"

        else:
            # Go to project page
            # Project page must end with a view
            # /productions/{project-id}/assets/
            # todo: maybe there's a better page than assets to go to?
            sub_url += "/assets"

        return f"{kitsu_url}{sub_url}"
