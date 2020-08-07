import functools
import time
from pype.api import Logger
import ftrack_api
from pype.modules.ftrack.ftrack_server.lib import SocketSession


class MissingPermision(Exception):
    def __init__(self, message=None):
        if message is None:
            message = 'Ftrack'
        super().__init__(message)


class PreregisterException(Exception):
    def __init__(self, message=None):
        if not message:
            message = "Pre-registration conditions were not met"
        super().__init__(message)


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
    ignore_me = False
    preactions = []

    def __init__(self, session, plugins_presets=None):
        '''Expects a ftrack_api.Session instance'''
        self.log = Logger().get_logger(self.__class__.__name__)
        if not(
            isinstance(session, ftrack_api.session.Session) or
            isinstance(session, SocketSession)
        ):
            raise Exception((
                "Session object entered with args is instance of \"{}\""
                " but expected instances are \"{}\" and \"{}\""
            ).format(
                str(type(session)),
                str(ftrack_api.session.Session),
                str(SocketSession)
            ))

        self._session = session

        # Using decorator
        self.register = self.register_decorator(self.register)
        self.launch = self.launch_log(self.launch)
        if plugins_presets is None:
            plugins_presets = {}
        self.plugins_presets = plugins_presets

    # Decorator
    def register_decorator(self, func):
        @functools.wraps(func)
        def wrapper_register(*args, **kwargs):

            presets_data = self.plugins_presets.get(self.__class__.__name__)
            if presets_data:
                for key, value in presets_data.items():
                    if not hasattr(self, key):
                        continue
                    setattr(self, key, value)

            if self.ignore_me:
                return

            label = self.__class__.__name__
            if hasattr(self, 'label'):
                if self.variant is None:
                    label = self.label
                else:
                    label = '{} {}'.format(self.label, self.variant)
            try:
                self._preregister()

                start_time = time.perf_counter()
                func(*args, **kwargs)
                end_time = time.perf_counter()
                run_time = end_time - start_time
                self.log.info((
                    '{} "{}" - Registered successfully ({:.4f}sec)'
                ).format(self.type, label, run_time))
            except MissingPermision as MPE:
                self.log.info((
                    '!{} "{}" - You\'re missing required {} permissions'
                ).format(self.type, label, str(MPE)))
            except AssertionError as ae:
                self.log.warning((
                    '!{} "{}" - {}'
                ).format(self.type, label, str(ae)))
            except NotImplementedError:
                self.log.error((
                    '{} "{}" - Register method is not implemented'
                ).format(self.type, label))
            except PreregisterException as exc:
                self.log.warning((
                    '{} "{}" - {}'
                ).format(self.type, label, str(exc)))
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
                label = self.label
                if hasattr(self, 'variant'):
                    if self.variant is not None:
                        label = '{} {}'.format(self.label, self.variant)

            self.log.info(('{} "{}": Launched').format(self.type, label))
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                self.session.rollback()
                msg = '{} "{}": Failed ({})'.format(self.type, label, str(exc))
                self.log.error(msg, exc_info=True)
                return {
                    'success': False,
                    'message': msg
                }
            finally:
                self.log.info(('{} "{}": Finished').format(self.type, label))
        return wrapper_launch

    @property
    def session(self):
        '''Return current session.'''
        return self._session

    def reset_session(self):
        self.session.reset()

    def _preregister(self):
        if hasattr(self, "role_list") and len(self.role_list) > 0:
            username = self.session.api_user
            user = self.session.query(
                'User where username is "{}"'.format(username)
            ).one()
            available = False
            lowercase_rolelist = [x.lower() for x in self.role_list]
            for role in user['user_security_roles']:
                if role['security_role']['name'].lower() in lowercase_rolelist:
                    available = True
                    break
            if available is False:
                raise MissingPermision

        # Custom validations
        result = self.preregister()
        if result is None:
            self.log.debug((
                "\"{}\" 'preregister' method returned 'None'. Expected it"
                " didn't fail and continue as preregister returned True."
            ).format(self.__class__.__name__))
            return

        if result is True:
            return
        msg = None
        if isinstance(result, str):
            msg = result
        raise PreregisterException(msg)

    def preregister(self):
        '''
        Preregister conditions.
        Registration continues if returns True.
        '''
        return True

    def register(self):
        '''
        Registers the action, subscribing the discover and launch topics.
        Is decorated by register_log
        '''

        raise NotImplementedError()

    def _translate_event(self, event, session=None):
        '''Return *event* translated structure to be used with the API.'''
        if session is None:
            session = self.session

        _entities = event['data'].get('entities_object', None)
        if (
            _entities is None or
            _entities[0].get(
                'link', None
            ) == ftrack_api.symbol.NOT_SET
        ):
            _entities = self._get_entities(event)
            event['data']['entities_object'] = _entities

        return _entities

    def _get_entities(self, event, session=None, ignore=None):
        entities = []
        selection = event['data'].get('selection')
        if not selection:
            return entities

        if ignore is None:
            ignore = []
        elif isinstance(ignore, str):
            ignore = [ignore]

        filtered_selection = []
        for entity in selection:
            if entity['entityType'] not in ignore:
                filtered_selection.append(entity)

        if not filtered_selection:
            return entities

        if session is None:
            session = self.session
            session._local_cache.clear()

        for entity in filtered_selection:
            entities.append(session.get(
                self._get_entity_type(entity, session),
                entity.get('entityId')
            ))

        return entities

    def _get_entity_type(self, entity, session=None):
        '''Return translated entity type tht can be used with API.'''
        # Get entity type and make sure it is lower cased. Most places except
        # the component tab in the Sidebar will use lower case notation.
        entity_type = entity.get('entityType').replace('_', '').lower()

        if session is None:
            session = self.session

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
        self.session.rollback()
        self.session._local_cache.clear()

        self.launch(self.session, event)

    def launch(self, session, event):
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

    def _handle_preactions(self, session, event):
        # If preactions are not set
        if len(self.preactions) == 0:
            return True
        # If no selection
        selection = event.get('data', {}).get('selection', None)
        if (selection is None):
            return False
        # If preactions were already started
        if event['data'].get('preactions_launched', None) is True:
            return True

        # Launch preactions
        for preaction in self.preactions:
            self.trigger_action(preaction, event)

        # Relaunch this action
        additional_data = {"preactions_launched": True}
        self.trigger_action(
            self.identifier, event, additional_event_data=additional_data
        )

        return False

    def _handle_result(self, result):
        '''Validate the returned result from the action callback'''
        if isinstance(result, bool):
            if result is True:
                result = {
                    'success': result,
                    'message': (
                        '{0} launched successfully.'.format(self.label)
                    )
                }
            else:
                result = {
                    'success': result,
                    'message': (
                        '{0} launch failed.'.format(self.label)
                    )
                }

        elif isinstance(result, dict):
            items = 'items' in result
            if items is False:
                for key in ('success', 'message'):
                    if key in result:
                        continue

                    raise KeyError(
                        'Missing required key: {0}.'.format(key)
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

    def show_interface(
        self, items, title='',
        event=None, user=None, username=None, user_id=None
    ):
        """
        Shows interface to user
        - to identify user must be entered one of args:
            event, user, username, user_id
        - 'items' must be list containing Ftrack interface items
        """
        if not any([event, user, username, user_id]):
            raise TypeError((
                'Missing argument `show_interface` requires one of args:'
                ' event (ftrack_api Event object),'
                ' user (ftrack_api User object)'
                ' username (string) or user_id (string)'
            ))

        if event:
            user_id = event['source']['user']['id']
        elif user:
            user_id = user['id']
        else:
            if user_id:
                key = 'id'
                value = user_id
            else:
                key = 'username'
                value = username

            user = self.session.query(
                'User where {} is "{}"'.format(key, value)
            ).first()

            if not user:
                raise TypeError((
                    'Ftrack user with {} "{}" was not found!'
                ).format(key, value))

            user_id = user['id']

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

    def show_interface_from_dict(
        self, messages, title="", event=None,
        user=None, username=None, user_id=None
    ):
        if not messages:
            self.log.debug("No messages to show! (messages dict is empty)")
            return
        items = []
        splitter = {'type': 'label', 'value': '---'}
        first = True
        for key, value in messages.items():
            if not first:
                items.append(splitter)
            else:
                first = False

            subtitle = {'type': 'label', 'value': '<h3>{}</h3>'.format(key)}
            items.append(subtitle)
            if isinstance(value, list):
                for item in value:
                    message = {
                        'type': 'label', 'value': '<p>{}</p>'.format(item)
                    }
                    items.append(message)
            else:
                message = {'type': 'label', 'value': '<p>{}</p>'.format(value)}
                items.append(message)

        self.show_interface(items, title, event, user, username, user_id)

    def trigger_action(
        self, action_name, event=None, session=None,
        selection=None, user_data=None,
        topic="ftrack.action.launch", additional_event_data={},
        on_error="ignore"
    ):
        self.log.debug("Triggering action \"{}\" Begins".format(action_name))

        if not session:
            session = self.session

        # Getting selection and user data
        _selection = None
        _user_data = None

        if event:
            _selection = event.get("data", {}).get("selection")
            _user_data = event.get("source", {}).get("user")

        if selection is not None:
            _selection = selection

        if user_data is not None:
            _user_data = user_data

        # Without selection and user data skip triggering
        msg = "Can't trigger \"{}\" action without {}."
        if _selection is None:
            self.log.error(msg.format(action_name, "selection"))
            return

        if _user_data is None:
            self.log.error(msg.format(action_name, "user data"))
            return

        _event_data = {
            "actionIdentifier": action_name,
            "selection": _selection
        }

        # Add additional data
        if additional_event_data:
            _event_data.update(additional_event_data)

        # Create and trigger event
        session.event_hub.publish(
            ftrack_api.event.base.Event(
                topic=topic,
                data=_event_data,
                source=dict(user=_user_data)
            ),
            on_error=on_error
        )
        self.log.debug(
            "Action \"{}\" Triggered successfully".format(action_name)
        )

    def trigger_event(
        self, topic, event_data={}, session=None, source=None,
        event=None, on_error="ignore"
    ):
        if session is None:
            session = self.session

        if not source and event:
            source = event.get("source")
        # Create and trigger event
        event = ftrack_api.event.base.Event(
            topic=topic,
            data=event_data,
            source=source
        )
        session.event_hub.publish(event, on_error=on_error)

        self.log.debug((
            "Publishing event: {}"
        ).format(str(event.__dict__)))

    def get_project_from_entity(self, entity):
        low_entity_type = entity.entity_type.lower()
        if low_entity_type == "project":
            return entity

        if "project" in entity:
            # reviewsession, task(Task, Shot, Sequence,...)
            return entity["project"]

        if low_entity_type == "filecomponent":
            entity = entity["version"]
            low_entity_type = entity.entity_type.lower()

        if low_entity_type == "assetversion":
            asset = entity["asset"]
            if asset:
                parent = asset["parent"]
                if parent:
                    return parent["project"]

        project_data = entity["link"][0]
        return self.session.query(
            "Project where id is {}".format(project_data["id"])
        ).one()
