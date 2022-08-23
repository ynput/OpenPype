import os
from .ftrack_base_handler import BaseHandler


def statics_icon(*icon_statics_file_parts):
    statics_server = os.environ.get("OPENPYPE_STATICS_SERVER")
    if not statics_server:
        return None
    return "/".join((statics_server, *icon_statics_file_parts))


class BaseAction(BaseHandler):
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
    type = 'Action'

    _discover_identifier = None
    _launch_identifier = None

    settings_frack_subkey = "user_handlers"
    settings_enabled_key = "enabled"

    def __init__(self, session):
        '''Expects a ftrack_api.Session instance'''
        if self.label is None:
            raise ValueError('Action missing label.')

        if self.identifier is None:
            raise ValueError('Action missing identifier.')

        super().__init__(session)

    @property
    def discover_identifier(self):
        if self._discover_identifier is None:
            self._discover_identifier = "{}.{}".format(
                self.identifier, self.process_identifier()
            )
        return self._discover_identifier

    @property
    def launch_identifier(self):
        if self._launch_identifier is None:
            self._launch_identifier = "{}.{}".format(
                self.identifier, self.process_identifier()
            )
        return self._launch_identifier

    def register(self):
        '''
        Registers the action, subscribing the the discover and launch topics.
        - highest priority event will show last
        '''
        self.session.event_hub.subscribe(
            'topic=ftrack.action.discover and source.user.username={0}'.format(
                self.session.api_user
            ),
            self._discover,
            priority=self.priority
        )

        launch_subscription = (
            'topic=ftrack.action.launch'
            ' and data.actionIdentifier={0}'
            ' and source.user.username={1}'
        ).format(
            self.launch_identifier,
            self.session.api_user
        )
        self.session.event_hub.subscribe(
            launch_subscription,
            self._launch
        )

    def _discover(self, event):
        entities = self._translate_event(event)
        if not entities:
            return

        accepts = self.discover(self.session, entities, event)
        if not accepts:
            return

        self.log.debug(u'Discovering action with selection: {0}'.format(
            event['data'].get('selection', [])
        ))

        return {
            'items': [{
                'label': self.label,
                'variant': self.variant,
                'description': self.description,
                'actionIdentifier': self.discover_identifier,
                'icon': self.icon,
            }]
        }

    def discover(self, session, entities, event):
        '''Return true if we can handle the selected entities.

        *session* is a `ftrack_api.Session` instance


        *entities* is a list of tuples each containing the entity type and the
        entity id. If the entity is a hierarchical you will always get the
        entity type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* the unmodified original event

        '''

        return False

    def _interface(self, session, entities, event):
        interface = self.interface(session, entities, event)
        if not interface:
            return

        if isinstance(interface, (tuple, list)):
            return {"items": interface}

        if isinstance(interface, dict):
            if (
                "items" in interface
                or ("success" in interface and "message" in interface)
            ):
                return interface

            raise ValueError((
                "Invalid interface output expected key: \"items\" or keys:"
                " \"success\" and \"message\". Got: \"{}\""
            ).format(str(interface)))

        raise ValueError(
            "Invalid interface output type \"{}\"".format(
                str(type(interface))
            )
        )

    def interface(self, session, entities, event):
        '''Return a interface if applicable or None

        *session* is a `ftrack_api.Session` instance

        *entities* is a list of tuples each containing the entity type and
        the entity id. If the entity is a hierarchical you will always get the
        entity type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* the unmodified original event
        '''
        return None

    def _launch(self, event):
        entities = self._translate_event(event)
        if not entities:
            return

        preactions_launched = self._handle_preactions(self.session, event)
        if preactions_launched is False:
            return

        interface = self._interface(self.session, entities, event)
        if interface:
            return interface

        response = self.launch(self.session, entities, event)

        return self._handle_result(response)

    def _handle_result(self, result):
        '''Validate the returned result from the action callback'''
        if isinstance(result, bool):
            if result is True:
                msg = 'Action {0} finished.'
            else:
                msg = 'Action {0} failed.'

            return {
                'success': result,
                'message': msg.format(self.label)
            }

        if isinstance(result, dict):
            if 'items' in result:
                if not isinstance(result['items'], list):
                    raise ValueError('Invalid items format, must be list!')

            else:
                for key in ('success', 'message'):
                    if key not in result:
                        raise KeyError(
                            "Missing required key: {0}.".format(key)
                        )
            return result

        self.log.warning((
            'Invalid result type \"{}\" must be bool or dictionary!'
        ).format(str(type(result))))

        return result

    @staticmethod
    def roles_check(settings_roles, user_roles, default=True):
        """Compare roles from setting and user's roles.

        Args:
            settings_roles(list): List of role names from settings.
            user_roles(list): User's lowered role names.
            default(bool): If `settings_roles` is empty list.

        Returns:
            bool: `True` if user has at least one role from settings or
                default if `settings_roles` is empty.
        """
        if not settings_roles:
            return default

        for role_name in settings_roles:
            if role_name.lower() in user_roles:
                return True
        return False

    @classmethod
    def get_user_entity_from_event(cls, session, event):
        """Query user entity from event."""
        not_set = object()

        # Check if user is already stored in event data
        user_entity = event["data"].get("user_entity", not_set)
        if user_entity is not_set:
            # Query user entity from event
            user_info = event.get("source", {}).get("user", {})
            user_id = user_info.get("id")
            username = user_info.get("username")
            if user_id:
                user_entity = session.query(
                    "User where id is {}".format(user_id)
                ).first()
            if not user_entity and username:
                user_entity = session.query(
                    "User where username is {}".format(username)
                ).first()
            event["data"]["user_entity"] = user_entity

        return user_entity

    @classmethod
    def get_user_roles_from_event(cls, session, event):
        """Query user entity from event."""
        not_set = object()

        user_roles = event["data"].get("user_roles", not_set)
        if user_roles is not_set:
            user_roles = []
            user_entity = cls.get_user_entity_from_event(session, event)
            for role in user_entity["user_security_roles"]:
                user_roles.append(role["security_role"]["name"].lower())
            event["data"]["user_roles"] = user_roles
        return user_roles

    def get_project_name_from_event(self, session, event, entities):
        """Load or query and fill project entity from/to event data.

        Project data are stored by ftrack id because in most cases it is
        easier to access project id than project name.

        Args:
            session (ftrack_api.Session): Current session.
            event (ftrack_api.Event): Processed event by session.
            entities (list): Ftrack entities of selection.
        """

        # Try to get project entity from event
        project_name = event["data"].get("project_name")
        if not project_name:
            project_entity = self.get_project_from_entity(
                entities[0], session
            )
            project_name = project_entity["full_name"]

            event["data"]["project_name"] = project_name
        return project_name

    def get_ftrack_settings(self, session, event, entities):
        project_name = self.get_project_name_from_event(
            session, event, entities
        )
        project_settings = self.get_project_settings_from_event(
            event, project_name
        )
        return project_settings["ftrack"]

    def valid_roles(self, session, entities, event):
        """Validate user roles by settings.

        Method requires to have set `settings_key` attribute.
        """
        ftrack_settings = self.get_ftrack_settings(session, event, entities)
        settings = (
            ftrack_settings[self.settings_frack_subkey][self.settings_key]
        )
        if self.settings_enabled_key:
            if not settings.get(self.settings_enabled_key, True):
                return False

        user_role_list = self.get_user_roles_from_event(session, event)
        if not self.roles_check(settings.get("role_list"), user_role_list):
            return False
        return True


class LocalAction(BaseAction):
    """Action that warn user when more Processes with same action are running.

    Action is launched all the time but if id does not match id of current
    instanace then message is shown to user.

    Handy for actions where matters if is executed on specific machine.
    """
    _full_launch_identifier = None

    @property
    def discover_identifier(self):
        if self._discover_identifier is None:
            self._discover_identifier = "{}.{}".format(
                self.identifier, self.process_identifier()
            )
        return self._discover_identifier

    @property
    def launch_identifier(self):
        """Catch all topics with same identifier."""
        if self._launch_identifier is None:
            self._launch_identifier = "{}.*".format(self.identifier)
        return self._launch_identifier

    @property
    def full_launch_identifier(self):
        """Catch all topics with same identifier."""
        if self._full_launch_identifier is None:
            self._full_launch_identifier = "{}.{}".format(
                self.identifier, self.process_identifier()
            )
        return self._full_launch_identifier

    def _discover(self, event):
        entities = self._translate_event(event)
        if not entities:
            return

        accepts = self.discover(self.session, entities, event)
        if not accepts:
            return

        self.log.debug("Discovering action with selection: {0}".format(
            event["data"].get("selection", [])
        ))

        return {
            "items": [{
                "label": self.label,
                "variant": self.variant,
                "description": self.description,
                "actionIdentifier": self.discover_identifier,
                "icon": self.icon,
            }]
        }

    def _launch(self, event):
        event_identifier = event["data"]["actionIdentifier"]
        # Check if identifier is same
        # - show message that acion may not be triggered on this machine
        if event_identifier != self.full_launch_identifier:
            return {
                "success": False,
                "message": (
                    "There are running more OpenPype processes"
                    " where this action could be launched."
                )
            }
        return super(LocalAction, self)._launch(event)


class ServerAction(BaseAction):
    """Action class meant to be used on event server.

    Unlike the `BaseAction` roles are not checked on register but on discover.
    For the same reason register is modified to not filter topics by username.
    """

    settings_frack_subkey = "events"

    @property
    def discover_identifier(self):
        return self.identifier

    @property
    def launch_identifier(self):
        return self.identifier

    def register(self):
        """Register subcription to Ftrack event hub."""
        self.session.event_hub.subscribe(
            "topic=ftrack.action.discover",
            self._discover,
            priority=self.priority
        )

        launch_subscription = (
            "topic=ftrack.action.launch and data.actionIdentifier={0}"
        ).format(self.launch_identifier)
        self.session.event_hub.subscribe(launch_subscription, self._launch)
