from avalon import api, io
from pype.clockify import ClockifyAPI
from pype.api import Logger
log = Logger.getLogger(__name__, "start_clockify")


class StartClockify(api.Action):

    name = "start_clockify_timer"
    label = "Start Timer - Clockify"
    icon = "clockify_icon"
    order = 500

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        if "AVALON_TASK" in session:
            return True
        return False

    def process(self, session, **kwargs):
        clockapi = ClockifyAPI()
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
            description = '/'.join(desc_items)

        clockapi.start_time_entry(
            description=description,
            project_name=project_name,
            task_name=task_name,
        )
