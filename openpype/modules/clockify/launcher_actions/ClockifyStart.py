from openpype.client import get_asset_by_name
from openpype.pipeline import LauncherAction
from openpype_modules.clockify.clockify_api import ClockifyAPI


class ClockifyStart(LauncherAction):
    name = "clockify_start_timer"
    label = "Clockify - Start Timer"
    icon = "app_icons/clockify.png"
    order = 500
    clockify_api = ClockifyAPI()

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        if "AVALON_TASK" in session:
            return True
        return False

    def process(self, session, **kwargs):
        self.clockify_api.set_api()
        user_id = self.clockify_api.user_id
        workspace_id = self.clockify_api.workspace_id
        project_name = session["AVALON_PROJECT"]
        asset_name = session["AVALON_ASSET"]
        task_name = session["AVALON_TASK"]
        description = asset_name

        # fetch asset docs
        asset_doc = get_asset_by_name(project_name, asset_name)

        # get task type to fill the timer tag
        task_info = asset_doc["data"]["tasks"][task_name]
        task_type = task_info["type"]

        # check if the task has hierarchy and fill the
        parents_data = asset_doc["data"]
        if parents_data is not None:
            description_items = parents_data.get("parents", [])
            description_items.append(asset_name)
            description_items.append(task_name)
            description = "/".join(description_items)

        project_id = self.clockify_api.get_project_id(
            project_name, workspace_id
        )
        tag_ids = []
        tag_name = task_type
        tag_ids.append(self.clockify_api.get_tag_id(tag_name, workspace_id))
        self.clockify_api.start_time_entry(
            description,
            project_id,
            tag_ids=tag_ids,
            workspace_id=workspace_id,
            user_id=user_id,
        )
