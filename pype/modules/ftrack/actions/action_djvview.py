import os
import subprocess
from operator import itemgetter
from pype.modules.ftrack.lib import BaseAction, statics_icon


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

        self.djv_path = self.find_djv_path()

    def preregister(self):
        if self.djv_path is None:
            return (
                'DJV View is not installed'
                ' or paths in presets are not set correctly'
            )
        return True

    def discover(self, session, entities, event):
        """Return available actions based on *event*. """
        selection = event["data"].get("selection", [])
        if len(selection) != 1:
            return False

        entityType = selection[0].get("entityType", None)
        if entityType in ["assetversion", "task"]:
            return True
        return False

    def find_djv_path(self):
        for path in (os.environ.get("DJV_PATH") or "").split(os.pathsep):
            if os.path.exists(path):
                return path

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

        items = []
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
                    items.append(
                        {'label': label, 'value': file_path}
                    )

        if len(items) == 0:
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
                items,
                key=itemgetter('label'),
                reverse=True
            )
        }
        if select_value is not None:
            item['value'] = select_value
        else:
            item['value'] = last_available

        return {'items': [item]}

    def launch(self, session, entities, event):
        """Callback method for DJVView action."""

        # Launching application
        if "values" not in event["data"]:
            return
        filpath = event['data']['values']['path']

        cmd = [
            # DJV path
            os.path.normpath(self.djv_path),
            # PATH TO COMPONENT
            os.path.normpath(filpath)
        ]

        try:
            # Run DJV with these commands
            subprocess.Popen(cmd)
        except FileNotFoundError:
            return {
                'success': False,
                'message': 'File "{}" was not found.'.format(
                    os.path.basename(filpath)
                )
            }

        return True


def register(session):
    """Register hooks."""

    DJVViewAction(session).register()
