import sys
import argparse
import logging
import getpass
import subprocess
import os

import ftrack_api
from ftrack_action_handler import BaseAction
import ft_utils

class openFolder(BaseAction):
    '''Open folders action'''

    #: Action identifier.
    identifier = 'open.folders'
    #: Action label.
    label = 'Open Folders'
    #: Action Icon.
    icon = "https://cdn3.iconfinder.com/data/icons/stroke/53/Open-Folder-256.png"
    raise ValueError('Not working version of action')

    def discover(self, session, entities, event):
        ''' Validation '''

        if len(entities) == 0 or entities[0].entity_type in ['assetversion', 'Component']:
            return False

        return True


    def get_paths(self, entity):
        '''Prepare all the paths for the entity.

        This function uses custom module to deal with paths.
        You will need to replace it with your logic.
        '''

        root = entity['project']['root']
        entity_type = entity.entity_type.lower()

        if entity_type == 'task':
            if entity['parent'].entity_type == 'Asset Build':
                templates = ['asset.task']
            else:
                templates = ['shot.task']

        elif entity_type in ['shot', 'folder', 'sequence', 'episode']:
                templates = ['shot']

        elif entity_type in ['asset build', 'library']:
                templates = ['asset']

        paths = ft_utils.getPathsYaml(entity,
                            templateList=templates,
                            root=root)
        return paths

    def launch(self, session, entities, event):
        '''Callback method for action.'''
        selection = event['data'].get('selection', [])
        self.logger.info(u'Launching action with selection \
                         {0}'.format(selection))

        # Prepare lists to keep track of failures and successes
        fails = []
        hits = set([])

        for entity in entities:

            # Get paths base on the entity.
            # This function needs to be chagned to fit your path logic
            paths = self.get_paths(entity)

            # For each path, check if it exists on the disk and try opening it
            for path in paths:
                if os.path.isdir(path):
                    self.logger.info('Opening: ' + path)

                    # open the folder
                    if sys.platform == 'darwin':
                        subprocess.Popen(['open', '--', path])
                    elif sys.platform == 'linux2':
                        subprocess.Popen(['gnome-open', '--', path])
                    elif sys.platform == 'win32':
                        subprocess.Popen(['explorer', path])

                    # add path to list of hits
                    hits.add(entity['name'])

            # Add entity to fails list if no folder could be openned for it
            if entity['name'] not in hits:
                fails.append(entity['name'])

        # Inform user of the result
        if len(hits) == 0:
            return {
                'success': False,
                'message': 'No folders found for: {}'.format(', '.join(fails))
            }

        if len(fails) > 0:
            return {
                'success': True,
                'message': 'No folders found for: {}'.format(', '.join(fails))
            }

        return {
            'success': True,
            'message': 'Opening folders'
        }


def register(session, **kw):
    '''Register action. Called when used as an event plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = openFolder(session)
    action_handler.register()


def main(arguments=None):
    '''Set up logging and register action.'''
    if arguments is None:
        arguments = []

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
