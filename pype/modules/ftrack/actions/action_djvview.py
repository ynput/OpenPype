import os
import sys
import logging
import subprocess
from operator import itemgetter
import ftrack_api
from pype.modules.ftrack.lib import BaseAction, statics_icon
from pype.api import Logger, config

log = Logger().get_logger(__name__)


class DJVViewAction(BaseAction):
    """Launch DJVView action."""
    identifier = "djvview-launch-action"
    label = "DJV View"
    description = "DJV View Launcher"
    icon = statics_icon("app_icons", "djvView.png")

    type = 'Application'

    def __init__(self, session, plugins_presets):
        '''Expects a ftrack_api.Session instance'''
        super().__init__(session, plugins_presets)
        self.djv_path = None

        self.config_data = config.get_presets()['djv_view']['config']
        self.set_djv_path()

        if self.djv_path is None:
            return

        self.allowed_types = self.config_data.get(
            'file_ext', ["img", "mov", "exr"]
        )

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

    def set_djv_path(self):
        for path in self.config_data.get("djv_paths", []):
            if os.path.exists(path):
                self.djv_path = path
                break

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
        default_component = self.config_data.get(
            'default_component', None
        )
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
        filename = event['data']['values']['path']

        fps = entities[0].get('custom_attributes', {}).get('fps', None)

        cmd = []
        # DJV path
        cmd.append(os.path.normpath(self.djv_path))
        # DJV Options Start ##############################################
        # '''layer name'''
        # cmd.append('-file_layer (value)')
        # ''' Proxy scale: 1/2, 1/4, 1/8'''
        # cmd.append('-file_proxy 1/2')
        # ''' Cache: True, False.'''
        # cmd.append('-file_cache True')
        # ''' Start in full screen '''
        # cmd.append('-window_fullscreen')
        # ''' Toolbar controls: False, True.'''
        # cmd.append("-window_toolbar False")
        # ''' Window controls: False, True.'''
        # cmd.append("-window_playbar False")
        # ''' Grid overlay: None, 1x1, 10x10, 100x100.'''
        # cmd.append("-view_grid None")
        # ''' Heads up display: True, False.'''
        # cmd.append("-view_hud True")
        ''' Playback: Stop, Forward, Reverse.'''
        cmd.append("-playback Forward")
        # ''' Frame.'''
        # cmd.append("-playback_frame (value)")
        if fps is not None:
            cmd.append("-playback_speed {}".format(int(fps)))
        # ''' Timer: Sleep, Timeout. Value: Sleep.'''
        # cmd.append("-playback_timer (value)")
        # ''' Timer resolution (seconds): 0.001.'''
        # cmd.append("-playback_timer_resolution (value)")
        ''' Time units: Timecode, Frames.'''
        cmd.append("-time_units Frames")
        # DJV Options End ################################################

        # PATH TO COMPONENT
        cmd.append(os.path.normpath(filename))

        try:
            # Run DJV with these commands
            subprocess.Popen(' '.join(cmd))
        except FileNotFoundError:
            return {
                'success': False,
                'message': 'File "{}" was not found.'.format(
                    os.path.basename(filename)
                )
            }

        return True


def register(session, plugins_presets={}):
    """Register hooks."""

    DJVViewAction(session, plugins_presets).register()


def main(arguments=None):
    '''Set up logging and register action.'''
    if arguments is None:
        arguments = []

    import argparse
    parser = argparse.ArgumentParser()
    # Allow setting of logging level from arguments.
    loggingLevels = {}
    for level in (
        logging.NOTSET, logging.DEBUG, logging.INFO, logging.WARNING,
        logging.ERROR, logging.CRITICAL
    ):
        loggingLevels[logging.getLevelName(level).lower()] = level

    parser.add_argument(
        '-v', '--verbosity',
        help='Set the logging output verbosity.',
        choices=loggingLevels.keys(),
        default='info'
    )
    namespace = parser.parse_args(arguments)

    # Set up basic logging
    logging.basicConfig(level=loggingLevels[namespace.verbosity])

    session = ftrack_api.Session()
    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
