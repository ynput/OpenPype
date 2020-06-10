import os
from .ftrack_base_handler import BaseHandler


def statics_icon(*icon_statics_file_parts):
    statics_server = os.environ.get("PYPE_STATICS_SERVER")
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

    def __init__(self, session, plugins_presets={}):
        '''Expects a ftrack_api.Session instance'''
        if self.label is None:
            raise ValueError('Action missing label.')

        if self.identifier is None:
            raise ValueError('Action missing identifier.')

        super().__init__(session, plugins_presets)

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
            self.identifier,
            self.session.api_user
        )
        self.session.event_hub.subscribe(
            launch_subscription,
            self._launch
        )

    def _discover(self, event):
        entities = self._translate_event(event)
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
                'actionIdentifier': self.identifier,
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

        preactions_launched = self._handle_preactions(self.session, event)
        if preactions_launched is False:
            return

        interface = self._interface(
            self.session, entities, event
        )

        if interface:
            return interface

        response = self.launch(
            self.session, entities, event
        )

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
