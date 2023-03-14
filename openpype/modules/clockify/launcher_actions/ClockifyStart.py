from openpype.client import get_asset_by_name
from openpype.pipeline import LauncherAction
from openpype_modules.clockify.clockify_api import ClockifyAPI


class ClockifyStart(LauncherAction):
    name = "clockify_start_timer"
    label = "Clockify - Start Timer"
    icon = "app_icons/clockify.png"
    order = 500
    clockapi = ClockifyAPI()

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        if "AVALON_TASK" in session:
            return True
        return False

    def process(self, session, **kwargs):
        self.clockapi.set_api()
        user_id = self.clockapi.user_id
        workspace_id = self.clockapi.workspace_id
        project_name = session["AVALON_PROJECT"]
        asset_name = session["AVALON_ASSET"]
        task_name = session["AVALON_TASK"]
        asset_doc = get_asset_by_name(project_name, asset_name)
        task_info = asset_doc["data"]["tasks"][task_name]
        task_type = task_info["type"]

        description = asset_name
        parents_data = get_asset_by_name(
            project_name, asset_name, fields=["data.parents"]
        )

        if parents_data is not None:
            desc_items = parents_data.get("data", {}).get("parents", [])
            desc_items.append(asset_name)
            desc_items.append(task_name)
            description = "/".join(desc_items)

        project_id = self.clockapi.get_project_id(project_name, workspace_id)
        tag_ids = []
        tag_name = task_type
        tag_ids.append(self.clockapi.get_tag_id(tag_name, workspace_id))
        self.clockapi.start_time_entry(
            description,
            project_id,
            tag_ids=tag_ids,
            workspace_id=workspace_id,
            user_id=user_id,
        )
