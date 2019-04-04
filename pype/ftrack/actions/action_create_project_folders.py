import os
import sys
import argparse
import logging
import json

import ftrack_api
from pype import lib as pypelib
from pype.ftrack import BaseAction


class CreateProjectFolders(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'create.project.folders'
    #: Action label.
    label = 'Create Project Folders'
    #: Action description.
    description = 'Creates folder structure'
    #: roles that are allowed to register this action
    role_list = ['Pypeclub', 'Administrator']
    icon = (
        'https://cdn2.iconfinder.com/data/icons/'
        'buttons-9/512/Button_Add-01.png'
    )

    def discover(self, session, entities, event):
        ''' Validation '''

        return True

    def launch(self, session, entities, event):
        preset_items = [
            pypelib.get_presets_path(),
            'tools',
            'project_folder_structure.json'
        ]
        filepath = os.path.sep.join(preset_items)

        # Load folder structure template from presets
        presets = dict()
        try:
            with open(filepath) as data_file:
                presets = json.load(data_file)
        except Exception as e:
            msg = 'Unable to load Folder structure preset'
            self.log.warning(msg)
            return {
                'success': False,
                'message': msg
            }

        # Set project root folder
        entity = entities[0]
        if entity.entity_type.lower() == 'project':
            project_name = entity['full_name']
        else:
            project_name = entity['project']['full_name']
        project_root_items = [os.environ['AVALON_PROJECTS'], project_name]
        project_root = os.path.sep.join(project_root_items)

        # Get paths based on presets
        paths = self.get_paths(presets)
        
        #Create folders
        for path in paths:
            os.makedirs(path.format(project_root=project_root))

        return True

    def get_paths(self, data, items=[]):
        paths = []
        path_items = []
        path_items.extend(items)
        name = data['name']
        if name == '__project_root__':
            name = '{project_root}'
        path_items.append(name)
        subfolders = data.get('subfolders', [])
        if len(subfolders) == 0:
            return os.path.sep.join(path_items)
        for sub in subfolders:
            result = self.get_paths(sub, path_items)
            if isinstance(result, str):
                paths.append(result)
            else:
                paths.extend(result)
        return paths


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    CreateProjectFolders(session).register()


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
