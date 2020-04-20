from .ftrack_base_handler import BaseHandler


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

    def _handle_result(self, session, result, entities, event):
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
            if 'items' in result:
                if not isinstance(result['items'], list):
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
