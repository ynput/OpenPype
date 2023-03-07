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

        return True

    def process(self, session, **kwargs):
        # Context inputs
        project_name = session["AVALON_PROJECT"]
        asset_name = session.get("AVALON_ASSET", None)
        task_name = session.get("AVALON_TASK", None)

        project = get_project(
            project_name=project_name, fields=["data.zou_id"]
        )
        if not project:
            raise RuntimeError("Project {} not found.".format(project_name))

        project_zou_id = project["data"].get("zou_id")
        if not project_zou_id:
            raise RuntimeError(
                "Project {} has no connected kitsu id.".format(project_name)
            )

        asset_zou_name = None
        asset_zou_id = None
        asset_zou_type = "Assets"
        task_zou_id = None
        zou_sub_type = ["AssetType", "Sequence"]
        if asset_name:
            asset_zou_name = asset_name
            asset_fields = ["data.zou.id", "data.zou.type"]
            if task_name:
                asset_fields.append("data.tasks.{}.zou.id".format(task_name))

            asset = get_asset_by_name(
                project_name, asset_name=asset_name, fields=asset_fields
            )

            asset_zou_data = asset["data"].get("zou")

            if asset_zou_data:
                asset_zou_type = asset_zou_data["type"]
                if asset_zou_type not in zou_sub_type:
                    asset_zou_id = asset_zou_data["id"]
            else:
                asset_zou_type = asset_name

            if task_name:
                task_data = asset["data"]["tasks"][task_name]
                task_zou_data = task_data.get("zou", {})
                if not task_zou_data:
                    self.log.debug(
                        "No zou task data for task: {}".format(task_name)
                    )
                task_zou_id = task_zou_data["id"]

        # Define URL
        url = self.get_url(
            project_id=project_zou_id,
            asset_name=asset_zou_name,
            asset_id=asset_zou_id,
            asset_type=asset_zou_type,
            task_id=task_zou_id,
        )

        # Open URL in webbrowser
        self.log.info("Opening URL: {}".format(url))
        webbrowser.open(
            url,
            # Try in new tab
            new=2,
        )

    def get_url(
        self,
        project_id,
        asset_name=None,
        asset_id=None,
        asset_type=None,
        task_id=None,
    ):
        shots_url = {"Shots", "Sequence", "Shot"}
        sub_type = {"AssetType", "Sequence"}
        kitsu_module = self.get_kitsu_module()

        # Get kitsu url with /api stripped
        kitsu_url = kitsu_module.server_url
        if kitsu_url.endswith("/api"):
            kitsu_url = kitsu_url[: -len("/api")]

        sub_url = f"/productions/{project_id}"
        asset_type_url = "shots" if asset_type in shots_url else "assets"

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
            # Add search method if is a sub_type
            sub_url += f"/{asset_type_url}"
            if asset_type in sub_type:
                sub_url += f"?search={asset_name}"

        return f"{kitsu_url}{sub_url}"
