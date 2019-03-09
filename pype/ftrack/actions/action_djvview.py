import os
import sys
import re
import json
import logging
import subprocess
from operator import itemgetter
import ftrack_api
from pype.ftrack import BaseHandler
from app.api import Logger
from pype import lib

log = Logger.getLogger(__name__)


class DJVViewAction(BaseHandler):
    """Launch DJVView action."""
    identifier = "djvview-launch-action"
    label = "DJV View"
    icon = "http://a.fsdn.com/allura/p/djv/icon"
    type = 'Application'

    def __init__(self, session):
        '''Expects a ftrack_api.Session instance'''
        super().__init__(session)
        self.variant = None
        self.djv_path = None
        self.config_data = None

        self.items = []
        if self.config_data is None:
            self.load_config_data()

        application = self.get_application()
        if application is None:
            return

        applicationIdentifier = application["identifier"]
        label = application["label"]
        self.items.append({
            "actionIdentifier": self.identifier,
            "label": label,
            "variant": application.get("variant", None),
            "description": application.get("description", None),
            "icon": application.get("icon", "default"),
            "applicationIdentifier": applicationIdentifier
        })

        if self.identifier is None:
            raise ValueError(
                'Action missing identifier.'
            )

    def is_valid_selection(self, event):
        selection = event["data"].get("selection", [])

        if not selection:
            return

        entityType = selection[0]["entityType"]

        if entityType not in ["assetversion", "task"]:
            return False

        return True

    def discover(self, event):
        """Return available actions based on *event*. """
        if self.djv_path is None:
            return
        if not self.is_valid_selection(event):
            return

        return {
            "items": self.items
        }

    def register(self):
        '''Registers the action, subscribing the discover and launch topics.'''
        self.session.event_hub.subscribe(
            'topic=ftrack.action.discover and source.user.username={0}'.format(
                self.session.api_user
                ), self.discover
        )
        launch_subscription = (
            'topic=ftrack.action.launch'
            ' and data.actionIdentifier={0}'
            ' and source.user.username={1}'
        )
        self.session.event_hub.subscribe(
            launch_subscription.format(
                self.identifier,
                self.session.api_user
            ),
            self.launch
        )

    def load_config_data(self):
        path_items = [lib.get_presets_path(), 'djv_view', 'config.json']
        filepath = os.path.sep.join(path_items)

        data = dict()
        try:
            with open(filepath) as data_file:
                data = json.load(data_file)
        except Exception as e:
            log.warning(
                'Failed to load data from DJV presets file ({})'.format(e)
            )

        self.config_data = data

    def get_application(self):
        applicationIdentifier = "djvview"
        description = "DJV View Launcher"

        possible_paths = self.config_data.get("djv_paths", [])
        for path in possible_paths:
            if os.path.exists(path):
                self.djv_path = path
                break

        if self.djv_path is None:
            log.debug("DJV View application was not found")
            return None

        application = {
            'identifier': applicationIdentifier,
            'label': self.label,
            'icon': self.icon,
            'description': description
        }

        versionExpression = re.compile(r"(?P<version>\d+.\d+.\d+)")
        versionMatch = versionExpression.search(self.djv_path)
        if versionMatch:
            new_label = '{} {}'.format(
                application['label'], versionMatch.group('version')
            )
            application['label'] = new_label

        return application

    def translate_event(self, session, event):
        '''Return *event* translated structure to be used with the API.'''

        selection = event['data'].get('selection', [])

        entities = list()
        for entity in selection:
            entities.append(
                (session.get(
                    self.get_entity_type(entity), entity.get('entityId')
                ))
            )

        return entities

    def get_entity_type(self, entity):
        entity_type = entity.get('entityType').replace('_', '').lower()

        for schema in self.session.schemas:
            alias_for = schema.get('alias_for')

            if (
                alias_for and isinstance(alias_for, str) and
                alias_for.lower() == entity_type
            ):
                return schema['id']

        for schema in self.session.schemas:
            if schema['id'].lower() == entity_type:
                return schema['id']

        raise ValueError(
            'Unable to translate entity type: {0}.'.format(entity_type)
        )

    def launch(self, event):
        """Callback method for DJVView action."""
        session = self.session
        entities = self.translate_event(session, event)

        # Launching application
        if "values" in event["data"]:
            filename = event['data']['values']['path']
            file_type = filename.split(".")[-1]

            # TODO Is this proper way?
            try:
                fps = int(entities[0]['custom_attributes']['fps'])
            except Exception:
                fps = 24

            # TODO issequence is probably already built-in validation in ftrack
            isseq = re.findall('%[0-9]*d', filename)
            if len(isseq) > 0:
                if len(isseq) == 1:
                    frames = []
                    padding = re.findall('%[0-9]*d', filename).pop()
                    index = filename.find(padding)

                    full_file = filename[0:index-1]
                    file = full_file.split(os.sep)[-1]
                    folder = os.path.dirname(full_file)

                    for fname in os.listdir(path=folder):
                        if fname.endswith(file_type) and file in fname:
                            frames.append(int(fname.split(".")[-2]))

                    if len(frames) > 0:
                        start = min(frames)
                        end = max(frames)

                        range = (padding % start) + '-' + (padding % end)
                        filename = re.sub('%[0-9]*d', range, filename)
                else:
                    msg = (
                        'DJV View - Filename has more than one'
                        ' sequence identifier.'
                    )
                    return {
                        'success': False,
                        'message': (msg)
                    }

            cmd = []
            # DJV path
            cmd.append(os.path.normpath(self.djv_path))
            # DJV Options Start ##############################################
            '''layer name'''
            # cmd.append('-file_layer (value)')
            ''' Proxy scale: 1/2, 1/4, 1/8'''
            cmd.append('-file_proxy 1/2')
            ''' Cache: True, False.'''
            cmd.append('-file_cache True')
            ''' Start in full screen '''
            # cmd.append('-window_fullscreen')
            ''' Toolbar controls: False, True.'''
            # cmd.append("-window_toolbar False")
            ''' Window controls: False, True.'''
            # cmd.append("-window_playbar False")
            ''' Grid overlay: None, 1x1, 10x10, 100x100.'''
            # cmd.append("-view_grid None")
            ''' Heads up display: True, False.'''
            # cmd.append("-view_hud True")
            ''' Playback: Stop, Forward, Reverse.'''
            cmd.append("-playback Forward")
            ''' Frame.'''
            # cmd.append("-playback_frame (value)")
            cmd.append("-playback_speed " + str(fps))
            ''' Timer: Sleep, Timeout. Value: Sleep.'''
            # cmd.append("-playback_timer (value)")
            ''' Timer resolution (seconds): 0.001.'''
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

            return {
                'success': True,
                'message': 'DJV View started.'
            }

        if 'items' not in event["data"]:
            event["data"]['items'] = []

        try:
            for entity in entities:
                versions = []
                self.load_config_data()
                default_types = ["img", "mov", "exr"]
                allowed_types = self.config_data.get('file_ext', default_types)

                if entity.entity_type.lower() == "assetversion":
                    if (
                        entity[
                            'components'
                        ][0]['file_type'][1:] in allowed_types
                    ):
                        versions.append(entity)

                elif entity.entity_type.lower() == "task":
                    # AssetVersions are obtainable only from shot!
                    shotentity = entity['parent']

                    for asset in shotentity['assets']:
                        for version in asset['versions']:
                            # Get only AssetVersion of selected task
                            if version['task']['id'] != entity['id']:
                                continue
                            # Get only components with allowed type
                            filetype = version['components'][0]['file_type']
                            if filetype[1:] in allowed_types:
                                versions.append(version)

                # Raise error if no components were found
                if len(versions) < 1:
                    raise ValueError('There are no Asset Versions to open.')

                for version in versions:
                    logging.info(version['components'])
                    for component in version['components']:
                        label = "v{0} - {1} - {2}"

                        label = label.format(
                            str(version['version']).zfill(3),
                            version['asset']['type']['name'],
                            component['name']
                        )

                        try:
                            # TODO This is proper way to get filepath!!!
                            location = component[
                                'component_locations'
                            ][0]['location']
                            file_path = location.get_filesystem_path(component)
                            # if component.isSequence():
                            #     if component.getMembers():
                            #         frame = int(
                            #             component.getMembers()[0].getName()
                            #         )
                            #         file_path = file_path % frame
                        except Exception:
                            # This works but is NOT proper way
                            file_path = component[
                                'component_locations'
                            ][0]['resource_identifier']

                        dirpath = os.path.dirname(file_path)
                        if os.path.isdir(dirpath):
                            event["data"]["items"].append(
                                {"label": label, "value": file_path}
                            )

                # Raise error if any component is playable
                if len(event["data"]["items"]) == 0:
                    raise ValueError(
                        'There are no Asset Versions with accessible path.'
                    )

        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }

        return {
            "items": [
                {
                    "label": "Items to view",
                    "type": "enumerator",
                    "name": "path",
                    "data": sorted(
                        event["data"]['items'],
                        key=itemgetter("label"),
                        reverse=True
                    )
                }
            ]
        }


def register(session):
    """Register hooks."""
    if not isinstance(session, ftrack_api.session.Session):
        return

    action = DJVViewAction(session)
    action.register()


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
