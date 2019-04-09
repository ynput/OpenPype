import os
import sys
import json
import argparse
import logging

import ftrack_api
from avalon import lib as avalonlib
from avalon.tools.libraryloader.io_nonsingleton import DbConnector
from pype import lib as pypelib
from pype.ftrack import BaseAction


class CreateSWFolders(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'create.sw.folders'
    #: Action label.
    label = 'Create SW Folders'
    #: Action description.
    description = 'Creates folders for all SW in project'


    def __init__(self, session):
        super().__init__(session)
        self.avalon_db = DbConnector()
        self.avalon_db.install()

    def discover(self, session, entities, event):
        ''' Validation '''

        return True

    def launch(self, session, entities, event):
        if len(entities) != 1:
            self.log.warning(
                'There are more entities in selection!'
            )
            return False
        entity = entities[0]
        if entity.entity_type.lower() != 'task':
            self.log.warning(
                'Selected entity is not Task!'
            )
            return False
        asset = entity['parent']
        project = asset['project']

        project_name = project["full_name"]
        self.avalon_db.Session['AVALON_PROJECT'] = project_name
        av_project = self.avalon_db.find_one({'type': 'project'})
        av_asset = self.avalon_db.find_one({
            'type': 'asset',
            'name': asset['name']
        })

        templates = av_project["config"]["template"]
        template = templates.get("work", None)
        if template is None:
            return False


        data = {
            "root": os.environ["AVALON_PROJECTS"],
            "project": {
                "name": project_name,
                "code": project["name"]
            },
            "hierarchy": av_asset['data']['hierarchy'],
            "asset": asset['name'],
            "task": entity['name'],
        }

        apps = []
        if '{app}' in template:
            # Apps in project
            for app in av_project['data']['applications']:
                app_data = avalonlib.get_application(app)
                app_dir = app_data['application_dir']
                if app_dir not in apps:
                    apps.append(app_dir)
        # Apps in presets
        path_items = [pypelib.get_presets_path(), 'tools', 'sw_folders.json']
        filepath = os.path.sep.join(path_items)

        presets = dict()
        try:
            with open(filepath) as data_file:
                presets = json.load(data_file)
        except Exception as e:
            self.log.warning('Wasn\'t able to load presets')
        preset_apps = presets.get(project_name, presets.get('__default__', []))
        for app in preset_apps:
            if app not in apps:
                apps.append(app)

        # Create folders for apps
        for app in apps:
            data['app'] = app
            self.log.info('Created folder for app {}'.format(app))
            path = os.path.normpath(template.format(**data))
            if os.path.exists(path):
                continue
            os.makedirs(path)

        return True


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    CreateSWFolders(session).register()


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
