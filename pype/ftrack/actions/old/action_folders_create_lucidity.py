import logging
import os
import getpass
import argparse
import errno
import sys
import threading
import ftrack

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


class CreateFolders(ftrack.Action):

    '''Custom action.'''

    #: Action identifier.
    identifier = 'create.folders'

    #: Action label.
    label = 'Create Folders'

    #: Action Icon.
    icon = 'https://cdn1.iconfinder.com/data/icons/rcons-folder-action/32/folder_add-512.png'

    def __init__(self):
        '''Initialise action handler.'''
        self.logger = logging.getLogger(
            __name__ + '.' + self.__class__.__name__
        )

    def register(self):
        '''Register action.'''
        ftrack.EVENT_HUB.subscribe(
            'topic=ftrack.action.discover and source.user.username={0}'.format(
                getpass.getuser()
            ),
            self.discover
        )

        ftrack.EVENT_HUB.subscribe(
            'topic=ftrack.action.launch and source.user.username={0} '
            'and data.actionIdentifier={1}'.format(
                getpass.getuser(), self.identifier
            ),
            self.launch
        )

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

    def validateSelection(self, selection):
        '''Return true if the selection is valid.

        '''
        if len(selection) == 0:
            return False

        entity = selection[0]
        task = ftrack.Task(entity['entityId'])

        if task.getObjectType() not in (
                'Episode', 'Sequence', 'Shot', 'Folder', 'Asset Build'):
            return False

        return True

    def discover(self, event):

        selection = event['data'].get('selection', [])

        self.logger.info(
            u'Discovering action with selection: {0}'.format(selection))

        if not self.validateSelection(selection):
            return

        return {
            'items': [{
                'label': self.label,
                'actionIdentifier': self.identifier,
                'icon': self.icon,
            }]
        }

    def launch(self, event):
        '''Callback method for custom action.'''
        selection = event['data'].get('selection', [])

        #######################################################################
        job = ftrack.createJob(
            description="Creating Folders", status="running")
        try:
            ftrack.EVENT_HUB.publishReply(
                event,
                data={
                    'success': True,
                    'message': 'Folder Creation Job Started!'
                }
            )

            for entity in selection:
                if entity['entityType'] == 'task':
                    entity = ftrack.Task(entity['entityId'])
                else:
                    entity = ftrack.Project(entity['entityId'])

                self.createFoldersFromEntity(entity)
            # inform the user that the job is done
            job.setStatus('done')
        except:
            job.setStatus('failed')
            raise

        #######################################################################

        return {
            'success': True,
            'message': 'Created Folders Successfully!'
        }


def register(registry, **kw):
    '''Register hooks.'''
    if registry is not ftrack.EVENT_HANDLERS:
        # Exit to avoid registering this plugin again.
        return
    logging.basicConfig(level=logging.DEBUG)
    action = CreateFolders()
    action.register()


def main(arguments=None):
    '''Create folders action.'''
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

    '''Register action and listen for events.'''
    logging.basicConfig(level=loggingLevels[namespace.verbosity])

    # Subscribe to action.
    ftrack.setup()
    action = CreateFolders()
    action.register()

    ftrack.EVENT_HUB.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
