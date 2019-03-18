import logging
import os
import argparse
import sys
import errno

import ftrack_api
from pype.ftrack import BaseAction
import json
from pype import api as pype


class CreateFolders(BaseAction):

    '''Custom action.'''

    #: Action identifier.
    identifier = 'create.folders'

    #: Action label.
    label = 'Create Folders'

    #: Action Icon.
    icon = (
        'https://cdn1.iconfinder.com/data/icons/hawcons/32/'
        '698620-icon-105-folder-add-512.png'
    )

    def discover(self, session, entities, event):
        ''' Validation '''

        return True

    def getShotAsset(self, entity):
        if entity not in self.importable:
            if entity['object_type']['name'] != 'Task':
                self.importable.add(entity)

        if entity['children']:
            children = entity['children']
            for child in children:
                self.getShotAsset(child)

    def launch(self, session, entities, event):
        '''Callback method for custom action.'''

        #######################################################################

        # JOB SETTINGS
        userId = event['source']['user']['id']
        user = session.query('User where id is ' + userId).one()

        job = session.create('Job', {
            'user': user,
            'status': 'running',
            'data': json.dumps({
                'description': 'Creating Folders.'
            })
        })

        try:
            self.importable = set([])
            # self.importable = []

            self.Anatomy = pype.Anatomy

            project = entities[0]['project']

            paths_collected = set([])

            # get all child entities separately/unique
            for entity in entities:
                self.getShotAsset(entity)

            for ent in self.importable:
                self.log.info("{}".format(ent['name']))

            for entity in self.importable:
                print(entity['name'])

                anatomy = pype.Anatomy
                parents = entity['link']

                hierarchy_names = []
                for p in parents[1:-1]:
                    hierarchy_names.append(p['name'])

                if hierarchy_names:
                    # hierarchy = os.path.sep.join(hierarchy)
                    hierarchy = os.path.join(*hierarchy_names)

                template_data = {"project": {"name": project['full_name'],
                                             "code": project['name']},
                                 "asset": entity['name'],
                                 "hierarchy": hierarchy}

                for task in entity['children']:
                    if task['object_type']['name'] == 'Task':
                        self.log.info('child: {}'.format(task['name']))
                        template_data['task'] = task['name']
                        anatomy_filled = anatomy.format(template_data)
                        paths_collected.add(anatomy_filled.work.folder)
                        paths_collected.add(anatomy_filled.publish.folder)

            for path in paths_collected:
                self.log.info(path)
                try:
                    os.makedirs(path)
                except OSError as error:
                    if error.errno != errno.EEXIST:
                        raise

            job['status'] = 'done'
            session.commit()

        except ValueError as ve:
            job['status'] = 'failed'
            session.commit()
            message = str(ve)
            self.log.error('Error during syncToAvalon: {}'.format(message))

        except Exception:
            job['status'] = 'failed'
            session.commit()

        #######################################################################

        return {
            'success': True,
            'message': 'Created Folders Successfully!'
        }


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    CreateFolders(session).register()


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
