import logging
import os
import getpass
import argparse
import errno
import sys
import threading
import ftrack_api
from ftrack_action_handler import BaseAction

PLUGIN_DIRECTORY = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))

if PLUGIN_DIRECTORY not in sys.path:
    sys.path.append(PLUGIN_DIRECTORY)

import ft_utils


def async(fn):
    '''Run *fn* asynchronously.'''
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
    return wrapper


class CreateFolders(BaseAction):

    #: Action identifier.
    identifier = 'create.folders'
    #: Action label.
    label = 'Create Folders'
    #: Action Icon.
    icon = 'https://cdn1.iconfinder.com/data/icons/rcons-folder-action/32/folder_add-512.png'

    raise ValueError('Not working version of action')
    @async
    def createFoldersFromEntity(self, entity):
        '''Generate folder structure from *entity*.

        Entity is assumed to be either a project, episode, sequence or shot.

        '''

        root = entity.getProject().getRoot()

        self.logger.info(root)

        if entity.getObjectType() in (
                'Episode', 'Sequence', 'Folder', 'Shot'):
            objects = entity.getChildren(objectType='Shot', depth=None)
            objects.append(entity)
        else:
            objects = entity.getChildren(depth=None)

        for obj in objects:

            tasks = obj.getTasks()
            paths_collected = set([])
            if obj.getObjectType() in (
                    'Episode', 'Sequence', 'Shot', 'Folder'):
                task_mask = 'shot.task'
            else:
                task_mask = 'asset.task'

            self.logger.info(task_mask)

            for task in tasks:
                self.logger.info(task)
                paths = ft_utils.getAllPathsYaml(task)
                self.logger.info(paths)
                for path in paths:
                    if task_mask in path[1].name:
                        temppath = os.path.join(
                            root, path[0].lower().replace(" ", '_').replace('\'', ''))
                        paths_collected.add(temppath)

            for path in paths_collected:
                self.logger.info(path)
                try:
                    os.makedirs(path)
                except OSError as error:
                    if error.errno != errno.EEXIST:
                        raise


    def discover(self, session, entities, event):

        if len(entities) == 0 or entities[0].entity_type not in [
                'Episode', 'Sequence', 'Shot', 'Folder', 'Asset Build']:
            return False

        return True


    def launch(self, session, entities, event):

        userId = event['source']['user']['id']
        user = session.query('User where id is ' + userId).one()

        job = session.create('Job', {
            'user': user,
            'status': 'running',
            'data': json.dumps({
                'description': 'Creating Folders'
            })
        })

        '''Callback method for custom action.'''

        try:
            session.event_hub.publishReply(
                event,
                data={
                    'success': True,
                    'message': 'Folder Creation Job Started!'
                }
            )

            for entity in entities:
                self.createFoldersFromEntity(entity)

            job.setStatus('done')
        except:
            job.setStatus('failed')
            raise


        return {
            'success': True,
            'message': 'Created Folders Successfully!'
        }


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = CreateFolders(session)
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
