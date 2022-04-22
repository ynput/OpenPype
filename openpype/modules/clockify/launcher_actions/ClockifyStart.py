from avalon import io

from openpype.api import Logger
from openpype.pipeline import LauncherAction
from openpype_modules.clockify.clockify_api import ClockifyAPI


log = Logger.get_logger(__name__)


class ClockifyStart(LauncherAction):

    name = "clockify_start_timer"
    label = "Clockify - Start Timer"
    icon = "clockify_icon"
    order = 500
    clockapi = ClockifyAPI()

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        if "AVALON_TASK" in session:
            return True
        return False

    def process(self, session, **kwargs):
        project_name = session['AVALON_PROJECT']
        asset_name = session['AVALON_ASSET']
        task_name = session['AVALON_TASK']

        description = asset_name
        asset = io.find_one({
            'type': 'asset',
            'name': asset_name
        })
        if asset is not None:
            desc_items = asset.get('data', {}).get('parents', [])
            desc_items.append(asset_name)
            desc_items.append(task_name)
            description = '/'.join(desc_items)

        project_id = self.clockapi.get_project_id(project_name)
        tag_ids = []
        tag_ids.append(self.clockapi.get_tag_id(task_name))
        self.clockapi.start_time_entry(
            description, project_id, tag_ids=tag_ids
        )
