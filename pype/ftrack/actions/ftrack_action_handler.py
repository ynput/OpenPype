# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack
import os
import sys
import platform
import ftrack_api
from avalon import lib
import acre
from pype.ftrack import ftrack_utils

from pype.ftrack import ftrack_utils
from pype import api as pype


ignore_me = True


class AppAction(object):
    '''Custom Action base class

    <label> - a descriptive string identifing your action.
    <varaint>   - To group actions together, give them the same
                  label and specify a unique variant per action.
    <identifier>  - a unique identifier for app.
    <description>   - a verbose descriptive text for you action
    <icon>  - icon in ftrack
     '''

    def __init__(
        self, session, label, name, executable,
        variant=None, icon=None, description=None
    ):
        '''Expects a ftrack_api.Session instance'''

        self.log = pype.Logger.getLogger(self.__class__.__name__)

        # self.logger = Logger.getLogger(__name__)

        if label is None:
            raise ValueError('Action missing label.')
        elif name is None:
            raise ValueError('Action missing identifier.')
        elif executable is None:
            raise ValueError('Action missing executable.')

        self._session = session
        self.label = label
        self.identifier = name
        self.executable = executable
        self.variant = variant
        self.icon = icon
        self.description = description

    @property
    def session(self):
        '''Return current session.'''
        return self._session

    def register(self, priority=100):
        '''Registers the action, subscribing the discover and launch topics.'''

        discovery_subscription = (
            'topic=ftrack.action.discover and source.user.username={0}'
        ).format(self.session.api_user)

        self.session.event_hub.subscribe(
            discovery_subscription,
            self._discover,
            priority=priority
        )

        launch_subscription = (
            'topic=ftrack.action.launch'
            ' and data.actionIdentifier={0}'
            ' and source.user.username={1}'
        ).format(
            self.identifier,
            self.session.api_user
        )
        self.session.event_hub.subscribe(
            launch_subscription,
            self._launch
        )
        self.log.info((
            "Application '{} {}' - Registered successfully"
        ).format(self.label, self.variant))

    def _discover(self, event):
        args = self._translate_event(
            self.session, event
        )

        accepts = self.discover(
            self.session, *args
        )

        if accepts:
            self.log.debug('Selection is valid')
            return {
                'items': [{
                    'label': self.label,
                    'variant': self.variant,
                    'description': self.description,
                    'actionIdentifier': self.identifier,
                    'icon': self.icon,
                }]
            }
        else:
            self.log.debug('Selection is _not_ valid')

    def discover(self, session, entities, event):
        '''Return true if we can handle the selected entities.

        *session* is a `ftrack_api.Session` instance

        *entities* is a list of tuples each containing the entity type and
        the entity id. If the entity is a hierarchical you will always get
        the entity type TypedContext, once retrieved through a get operation
        you will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* the unmodified original event

        '''

        entity_type, entity_id = entities[0]
        entity = session.get(entity_type, entity_id)

        # TODO Should return False if not TASK ?!!!
        # TODO Should return False if more than one entity is selected ?!!!
        if (
            len(entities) > 1 or
            entity.entity_type.lower() != 'task'
        ):
            return False

        ft_project = entity['project']

        database = ftrack_utils.get_avalon_database()
        project_name = ft_project['full_name']
        avalon_project = database[project_name].find_one({
            "type": "project"
        })

        if avalon_project is None:
            return False
        else:
            apps = []
            for app in avalon_project['config']['apps']:
                apps.append(app['name'])

            if self.identifier not in apps:
                return False

        return True

    def _translate_event(self, session, event):
        '''Return *event* translated structure to be used with the API.'''

        _selection = event['data'].get('selection', [])

        _entities = list()
        for entity in _selection:
            _entities.append(
                (
                    self._get_entity_type(entity), entity.get('entityId')
                )
            )

        return [
            _entities,
            event
        ]

    def _get_entity_type(self, entity):
        '''Return translated entity type tht can be used with API.'''
        # Get entity type and make sure it is lower cased. Most places except
        # the component tab in the Sidebar will use lower case notation.
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

    def _launch(self, event):
        args = self._translate_event(
            self.session, event
        )

        interface = self._interface(
            self.session, *args
        )

        if interface:
            return interface

        response = self.launch(
            self.session, *args
        )

        return self._handle_result(
            self.session, response, *args
        )

    def launch(self, session, entities, event):
        '''Callback method for the custom action.

        return either a bool ( True if successful or False if the action failed )
        or a dictionary with they keys `message` and `success`, the message should be a
        string and will be displayed as feedback to the user, success should be a bool,
        True if successful or False if the action failed.

        *session* is a `ftrack_api.Session` instance

        *entities* is a list of tuples each containing the entity type and the entity id.
        If the entity is a hierarchical you will always get the entity
        type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* the unmodified original event

        '''

        self.log.info((
            "Action - {0} ({1}) - just started"
        ).format(self.label, self.identifier))

        entity, id = entities[0]
        entity = session.get(entity, id)
        project_name = entity['project']['full_name']

        database = ftrack_utils.get_avalon_database()

        # Get current environments
        env_list = [
            'AVALON_PROJECT',
            'AVALON_SILO',
            'AVALON_ASSET',
            'AVALON_TASK',
            'AVALON_APP',
            'AVALON_APP_NAME'
        ]
        env_origin = {}
        for env in env_list:
            env_origin[env] = os.environ.get(env, None)

        # set environments for Avalon
        os.environ["AVALON_PROJECT"] = project_name
        os.environ["AVALON_SILO"] = entity['ancestors'][0]['name']
        os.environ["AVALON_ASSET"] = entity['parent']['name']
        os.environ["AVALON_TASK"] = entity['name']
        os.environ["AVALON_APP"] = self.identifier.split("_")[0]
        os.environ["AVALON_APP_NAME"] = self.identifier

        anatomy = pype.Anatomy
        hierarchy = database[project_name].find_one({
            "type": 'asset',
            "name": entity['parent']['name']
        })['data']['parents']

        if hierarchy:
            hierarchy = os.path.join(*hierarchy)

        data = {"project": {"name": entity['project']['full_name'],
                            "code": entity['project']['name']},
                "task": entity['name'],
                "asset": entity['parent']['name'],
                "hierarchy": hierarchy}
        try:
            anatomy = anatomy.format(data)
        except Exception as e:
            self.log.error(
                "{0} Error in anatomy.format: {1}".format(__name__, e)
            )
        os.environ["AVALON_WORKDIR"] = os.path.join(
            anatomy.work.root, anatomy.work.folder
        )

        # collect all parents from the task
        parents = []
        for item in entity['link']:
            parents.append(session.get(item['type'], item['id']))

        # collect all the 'environment' attributes from parents
        tools_attr = [os.environ["AVALON_APP"], os.environ["AVALON_APP_NAME"]]
        for parent in reversed(parents):
            # check if the attribute is empty, if not use it
            if parent['custom_attributes']['tools_env']:
                tools_attr.extend(parent['custom_attributes']['tools_env'])
                break

        tools_env = acre.get_tools(tools_attr)
        env = acre.compute(tools_env)
        env = acre.merge(env, current_env=dict(os.environ))

        # Get path to execute
        st_temp_path = os.environ['PYPE_STUDIO_TEMPLATES']
        os_plat = platform.system().lower()

        # Path to folder with launchers
        path = os.path.join(st_temp_path, 'bin', os_plat)
        # Full path to executable launcher
        execfile = None

        if sys.platform == "win32":

            for ext in os.environ["PATHEXT"].split(os.pathsep):
                fpath = os.path.join(path.strip('"'), self.executable + ext)
                if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
                    execfile = fpath
                    break
                pass

            # Run SW if was found executable
            if execfile is not None:
                lib.launch(executable=execfile, args=[], environment=env)
            else:
                return {
                    'success': False,
                    'message': "We didn't found launcher for {0}"
                    .format(self.label)
                    }
                pass

        if sys.platform.startswith('linux'):
            execfile = os.path.join(path.strip('"'), self.executable)
            if os.path.isfile(execfile):
                try:
                    fp = open(execfile)
                except PermissionError as p:
                    self.log.error('Access denied on {0} - {1}'.format(
                        execfile, p))
                    return {
                        'success': False,
                        'message': "Access denied on launcher - {}".format(
                            execfile)
                    }
                fp.close()
                # check executable permission
                if not os.access(execfile, os.X_OK):
                    self.log.error('No executable permission on {}'.format(
                        execfile))
                    return {
                        'success': False,
                        'message': "No executable permission - {}".format(
                            execfile)
                        }
                    pass
            else:
                self.log.error('Launcher doesn\'t exist - {}'.format(
                    execfile))
                return {
                    'success': False,
                    'message': "Launcher doesn't exist - {}".format(execfile)
                }
                pass
            # Run SW if was found executable
            if execfile is not None:
                lib.launch(
                    '/usr/bin/env', args=['bash', execfile], environment=env
                )
            else:
                return {
                    'success': False,
                    'message': "We didn't found launcher for {0}"
                    .format(self.label)
                    }
                pass

        # RUN TIMER IN FTRACK
        username = event['source']['user']['username']
        user_query = 'User where username is "{}"'.format(username)
        user = session.query(user_query).one()
        task = session.query('Task where id is {}'.format(entity['id'])).one()
        self.log.info('Starting timer for task: ' + task['name'])
        user.start_timer(task, force=True)

        # Change status of task to In progress
        config = ftrack_utils.get_config_data()

        if (
            'status_on_app_launch' in config and
            'sync_to_avalon' in config and
            'statuses_name_change' in config['sync_to_avalon']
        ):
            statuses = config['sync_to_avalon']['statuses_name_change']
            if entity['status']['name'].lower() in statuses:
                status_name = config['status_on_app_launch']

                try:
                    query = 'Status where name is "{}"'.format(status_name)
                    status = session.query(query).one()
                    task['status'] = status
                    session.commit()
                except Exception as e:
                    msg = "Status '{}' in config wasn't found on Ftrack".format(status_name)
                    self.log.warning(msg)

        # Set origin avalon environments
        for key, value in env_origin.items():
            os.environ[key] = value

        return {
            'success': True,
            'message': "Launching {0}".format(self.label)
        }

    def _interface(self, *args):
        interface = self.interface(*args)

        if interface:
            return {
                'items': interface
            }

    def interface(self, session, entities, event):
        '''Return a interface if applicable or None

        *session* is a `ftrack_api.Session` instance

        *entities* is a list of tuples each containing the entity type and the entity id.
        If the entity is a hierarchical you will always get the entity
        type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* the unmodified original event
        '''
        return None

    def _handle_result(self, session, result, entities, event):
        '''Validate the returned result from the action callback'''
        if isinstance(result, bool):
            result = {
                'success': result,
                'message': (
                    '{0} launched successfully.'.format(
                        self.label
                    )
                )
            }

        elif isinstance(result, dict):
            for key in ('success', 'message'):
                if key in result:
                    continue

                raise KeyError(
                    'Missing required key: {0}.'.format(key)
                )

        else:
            self.log.error(
                'Invalid result type must be bool or dictionary!'
            )

        return result


class BaseAction(object):
    '''Custom Action base class

    `label` a descriptive string identifing your action.

    `varaint` To group actions together, give them the same
    label and specify a unique variant per action.

    `identifier` a unique identifier for your action.

    `description` a verbose descriptive text for you action

     '''
    label = None
    variant = None
    identifier = None
    description = None
    icon = None

    def __init__(self, session):
        '''Expects a ftrack_api.Session instance'''

        self.log = pype.Logger.getLogger(self.__class__.__name__)

        if self.label is None:
            raise ValueError(
                'Action missing label.'
            )

        elif self.identifier is None:
            raise ValueError(
                'Action missing identifier.'
            )

        self._session = session

    @property
    def session(self):
        '''Return current session.'''
        return self._session

    def reset_session(self):
        self.session.reset()

    def register(self, priority=100):
        '''
        Registers the action, subscribing the the discover and launch topics.
        - highest priority event will show last
        '''
        self.session.event_hub.subscribe(
            'topic=ftrack.action.discover and source.user.username={0}'.format(
                self.session.api_user
            ), self._discover, priority=priority
        )

        launch_subscription = (
            'topic=ftrack.action.launch'
            ' and data.actionIdentifier={0}'
            ' and source.user.username={1}'
        ).format(
            self.identifier,
            self.session.api_user
        )
        self.session.event_hub.subscribe(
            launch_subscription,
            self._launch
        )

        self.log.info("Action '{}' - Registered successfully".format(
            self.__class__.__name__))

    def _discover(self, event):
        args = self._translate_event(
            self.session, event
        )

        accepts = self.discover(
            self.session, *args
        )

        if accepts:
            self.log.info(u'Discovering action with selection: {0}'.format(
                args[1]['data'].get('selection', [])))
            return {
                'items': [{
                    'label': self.label,
                    'variant': self.variant,
                    'description': self.description,
                    'actionIdentifier': self.identifier,
                    'icon': self.icon,
                }]
            }

    def discover(self, session, entities, event):
        '''Return true if we can handle the selected entities.

        *session* is a `ftrack_api.Session` instance


        *entities* is a list of tuples each containing the entity type and the entity id.
        If the entity is a hierarchical you will always get the entity
        type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* the unmodified original event

        '''

        return False

    def _translate_event(self, session, event):
        '''Return *event* translated structure to be used with the API.'''

        _selection = event['data'].get('selection', [])

        _entities = list()
        for entity in _selection:
            _entities.append(
                (
                    session.get(
                        self._get_entity_type(entity),
                        entity.get('entityId')
                    )
                )
            )

        return [
            _entities,
            event
        ]

    def _get_entity_type(self, entity):
        '''Return translated entity type tht can be used with API.'''
        # Get entity type and make sure it is lower cased. Most places except
        # the component tab in the Sidebar will use lower case notation.
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

    def _launch(self, event):
        self.reset_session()
        args = self._translate_event(
            self.session, event
        )

        interface = self._interface(
            self.session, *args
        )

        if interface:
            return interface

        response = self.launch(
            self.session, *args
        )

        return self._handle_result(
            self.session, response, *args
        )

    def launch(self, session, entities, event):
        '''Callback method for the custom action.

        return either a bool ( True if successful or False if the action failed )
        or a dictionary with they keys `message` and `success`, the message should be a
        string and will be displayed as feedback to the user, success should be a bool,
        True if successful or False if the action failed.

        *session* is a `ftrack_api.Session` instance

        *entities* is a list of tuples each containing the entity type and the entity id.
        If the entity is a hierarchical you will always get the entity
        type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* the unmodified original event

        '''
        raise NotImplementedError()

    def _interface(self, *args):
        interface = self.interface(*args)

        if interface:
            return {
                'items': interface
            }

    def interface(self, session, entities, event):
        '''Return a interface if applicable or None

        *session* is a `ftrack_api.Session` instance

        *entities* is a list of tuples each containing the entity type and the entity id.
        If the entity is a hierarchical you will always get the entity
        type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* the unmodified original event
        '''
        return None

    def show_message(self, event, input_message, result=False):
        """
        Shows message to user who triggered event
        - event - just source of user id
        - input_message - message that is shown to user
        - result - changes color of message (based on ftrack settings)
            - True = Violet
            - False = Red
        """
        if not isinstance(result, bool):
            result = False

        try:
            message = str(input_message)
        except Exception:
            return

        user_id = event['source']['user']['id']
        target = (
            'applicationId=ftrack.client.web and user.id="{0}"'
        ).format(user_id)
        self.session.event_hub.publish(
            ftrack_api.event.base.Event(
                topic='ftrack.action.trigger-user-interface',
                data=dict(
                    type='message',
                    success=result,
                    message=message
                ),
                target=target
            ),
            on_error='ignore'
        )

    def _handle_result(self, session, result, entities, event):
        '''Validate the returned result from the action callback'''
        if isinstance(result, bool):
            result = {
                'success': result,
                'message': (
                    '{0} launched successfully.'.format(
                        self.label
                    )
                )
            }

        elif isinstance(result, dict):
            if 'items' in result:
                items = result['items']
                if not isinstance(items, list):
                    raise ValueError('Invalid items format, must be list!')

            else:
                for key in ('success', 'message'):
                    if key in result:
                        continue

                    raise KeyError(
                        'Missing required key: {0}.'.format(key)
                    )

        else:
            self.log.error(
                'Invalid result type must be bool or dictionary!'
            )

        return result

    def show_interface(self, event, items, title=''):
        """
        Shows interface to user who triggered event
        - 'items' must be list containing Ftrack interface items
        """
        user_id = event['source']['user']['id']
        target = (
            'applicationId=ftrack.client.web and user.id="{0}"'
        ).format(user_id)

        self.session.event_hub.publish(
            ftrack_api.event.base.Event(
                topic='ftrack.action.trigger-user-interface',
                data=dict(
                    type='widget',
                    items=items,
                    title=title
                ),
                target=target
            ),
            on_error='ignore'
        )
