import os
import time
import subprocess
from operator import itemgetter
from openpype.lib import ApplicationManager
from openpype_modules.ftrack.lib import BaseAction, statics_icon


class DJVViewAction(BaseAction):
    """Launch DJVView action."""
    identifier = "djvview-launch-action"
    label = "DJV View"
    description = "DJV View Launcher"
    icon = statics_icon("app_icons", "djvView.png")

    type = 'Application'

    allowed_types = [
        "cin", "dpx", "avi", "dv", "gif", "flv", "mkv", "mov", "mpg", "mpeg",
        "mp4", "m4v", "mxf", "iff", "z", "ifl", "jpeg", "jpg", "jfif", "lut",
        "1dl", "exr", "pic", "png", "ppm", "pnm", "pgm", "pbm", "rla", "rpf",
        "sgi", "rgba", "rgb", "bw", "tga", "tiff", "tif", "img"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.application_manager = ApplicationManager()
        self._last_check = time.time()
        self._check_interval = 10

    def _get_djv_apps(self):
        app_group = self.application_manager.app_groups["djvview"]

        output = []
        for app in app_group:
            executable = app.find_executable()
            if executable is not None:
                output.append(app)
        return output

    def get_djv_apps(self):
        cur_time = time.time()
        if (cur_time - self._last_check) > self._check_interval:
            self.application_manager.refresh()
        return self._get_djv_apps()

    def discover(self, session, entities, event):
        """Return available actions based on *event*. """
        selection = event["data"].get("selection", [])
        if len(selection) != 1:
            return False

        entityType = selection[0].get("entityType", None)
        if entityType not in ["assetversion", "task"]:
            return False

        if self.get_djv_apps():
            return True
        return False

    def interface(self, session, entities, event):
        if event['data'].get('values', {}):
            return

        entity = entities[0]
        versions = []

        entity_type = entity.entity_type.lower()
        if entity_type == "assetversion":
            if (
                entity[
                    'components'
                ][0]['file_type'][1:] in self.allowed_types
            ):
                versions.append(entity)
        else:
            master_entity = entity
            if entity_type == "task":
                master_entity = entity['parent']

            for asset in master_entity['assets']:
                for version in asset['versions']:
                    # Get only AssetVersion of selected task
                    if (
                        entity_type == "task" and
                        version['task']['id'] != entity['id']
                    ):
                        continue
                    # Get only components with allowed type
                    filetype = version['components'][0]['file_type']
                    if filetype[1:] in self.allowed_types:
                        versions.append(version)

        if len(versions) < 1:
            return {
                'success': False,
                'message': 'There are no Asset Versions to open.'
            }

        # TODO sort them (somehow?)
        enum_items = []
        first_value = None
        for app in self.get_djv_apps():
            if first_value is None:
                first_value = app.full_name
            enum_items.append({
                "value": app.full_name,
                "label": app.full_label
            })

        if not enum_items:
            return {
                "success": False,
                "message": "Couldn't find DJV executable."
            }

        items = [
            {
                "type": "enumerator",
                "label": "DJV version:",
                "name": "djv_app_name",
                "data": enum_items,
                "value": first_value
            },
            {
                "type": "label",
                "value": "---"
            }
        ]
        version_items = []
        base_label = "v{0} - {1} - {2}"
        default_component = None
        last_available = None
        select_value = None
        for version in versions:
            for component in version['components']:
                label = base_label.format(
                    str(version['version']).zfill(3),
                    version['asset']['type']['name'],
                    component['name']
                )

                try:
                    location = component[
                        'component_locations'
                    ][0]['location']
                    file_path = location.get_filesystem_path(component)
                except Exception:
                    file_path = component[
                        'component_locations'
                    ][0]['resource_identifier']

                if os.path.isdir(os.path.dirname(file_path)):
                    last_available = file_path
                    if component['name'] == default_component:
                        select_value = file_path
                    version_items.append(
                        {'label': label, 'value': file_path}
                    )

        if len(version_items) == 0:
            return {
                'success': False,
                'message': (
                    'There are no Asset Versions with accessible path.'
                )
            }

        item = {
            'label': 'Items to view',
            'type': 'enumerator',
            'name': 'path',
            'data': sorted(
                version_items,
                key=itemgetter('label'),
                reverse=True
            )
        }
        if select_value is not None:
            item['value'] = select_value
        else:
            item['value'] = last_available

        items.append(item)

        return {'items': items}

    def launch(self, session, entities, event):
        """Callback method for DJVView action."""

        # Launching application
        event_data = event["data"]
        if "values" not in event_data:
            return

        djv_app_name = event_data["djv_app_name"]
        app = self.applicaion_manager.applications.get(djv_app_name)
        executable = None
        if app is not None:
            executable = app.find_executable()

        if not executable:
            return {
                "success": False,
                "message": "Couldn't find DJV executable."
            }

        filpath = os.path.normpath(event_data["values"]["path"])

        cmd = [
            # DJV path
            executable,
            # PATH TO COMPONENT
            filpath
        ]

        try:
            # Run DJV with these commands
            subprocess.Popen(cmd)
        except FileNotFoundError:
            return {
                "success": False,
                "message": "File \"{}\" was not found.".format(
                    os.path.basename(filpath)
                )
            }

        return True


def register(session):
    """Register hooks."""

    DJVViewAction(session).register()
