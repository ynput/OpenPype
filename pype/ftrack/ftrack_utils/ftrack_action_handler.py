# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack
import ftrack_api
from pype import api as pype


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
            self.log.debug(u'Discovering action with selection: {0}'.format(
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
            if 'items' in interface:
                return interface

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
