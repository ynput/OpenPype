import ftrack_api
import functools
import time
from pype import api as pype


class MissingPermision(Exception):
     def __init__(self):
        super().__init__('Missing permission')


class BaseHandler(object):
    '''Custom Action base class

    <label> - a descriptive string identifing your action.
    <varaint>   - To group actions together, give them the same
                  label and specify a unique variant per action.
    <identifier>  - a unique identifier for app.
    <description>   - a verbose descriptive text for you action
    <icon>  - icon in ftrack
    '''
    # Default priority is 100
    priority = 100
    # Type is just for logging purpose (e.g.: Action, Event, Application,...)
    type = 'No-type'

    def __init__(self, session):
        '''Expects a ftrack_api.Session instance'''
        self._session = session
        self.log = pype.Logger.getLogger(self.__class__.__name__)

        # Using decorator
        self.register = self.register_decorator(self.register)
        self.launch = self.launch_log(self.launch)

    # Decorator
    def register_decorator(self, func):
        @functools.wraps(func)
        def wrapper_register(*args, **kwargs):
            label = self.__class__.__name__
            if hasattr(self, 'label'):
                if self.variant is None:
                    label = self.label
                else:
                    label = '{} {}'.format(self.label, self.variant)
            try:
                if hasattr(self, "role_list") and len(self.role_list) > 0:
                    username = self.session.api_user
                    user = self.session.query(
                        'User where username is "{}"'.format(username)
                    ).one()
                    available = False
                    for role in user['user_security_roles']:
                        if role['security_role']['name'] in self.role_list:
                            available = True
                            break
                    if available is False:
                        raise MissingPermision

                start_time = time.perf_counter()
                func(*args, **kwargs)
                end_time = time.perf_counter()
                run_time = end_time - start_time
                self.log.info((
                    '{} "{}" - Registered successfully ({:.4f}sec)'
                ).format(self.type, label, run_time))
            except MissingPermision:
                self.log.info((
                    '!{} "{}" - You\'re missing required permissions'
                ).format(self.type, label))
            except NotImplementedError:
                self.log.error((
                    '{} "{}" - Register method is not implemented'
                ).format(
                    self.type, label)
                )
            except Exception as e:
                self.log.error('{} "{}" - Registration failed ({})'.format(
                    self.type, label, str(e))
                )
        return wrapper_register

    # Decorator
    def launch_log(self, func):
        @functools.wraps(func)
        def wrapper_launch(*args, **kwargs):
            label = self.__class__.__name__
            if hasattr(self, 'label'):
                if self.variant is None:
                    label = self.label
                else:
                    label = '{} {}'.format(self.label, self.variant)

            try:
                result = func(*args, **kwargs)
                self.log.info((
                    '{} "{}" Launched'
                ).format(self.type, label))
                return result
            except Exception as e:
                self.log.error('{} "{}": Launch failed ({})'.format(
                    self.type, label, str(e))
                )
        return wrapper_launch

    @property
    def session(self):
        '''Return current session.'''
        return self._session

    def reset_session(self):
        self.session.reset()

    def register(self):
        '''
        Registers the action, subscribing the discover and launch topics.
        Is decorated by register_log
        '''

        raise NotImplementedError()

    def _discover(self, event):
        items = {
            'items': [{
                'label': self.label,
                'variant': self.variant,
                'description': self.description,
                'actionIdentifier': self.identifier,
                'icon': self.icon,
            }]
        }
        accepts = self.prediscover(event)
        if accepts is None:
            args = self._translate_event(
                self.session, event
            )

            accepts = self.discover(
                self.session, *args
            )

        if accepts is True:
            self.log.debug(u'Discovering action with selection: {0}'.format(
                event['data'].get('selection', [])))
            return items

    def prediscover(self, event):
        "return True if can handle selected entities before handling entities"
        return None

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

        '''Return *event* translated structure to be used with the API.'''
        _entities = event['data'].get('entities', None)
        if _entities is None:
            selection = event['data'].get('selection', [])
            _entities = []
            for entity in selection:
                _entities.append(
                    self.session.get(
                        self._get_entity_type(entity),
                        entity.get('entityId')
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
