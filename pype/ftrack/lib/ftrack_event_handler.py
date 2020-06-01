import functools
from .ftrack_base_handler import BaseHandler


class BaseEvent(BaseHandler):
    '''Custom Event base class

    BaseEvent is based on ftrack.update event
    - get entities from event

    If want to use different event base
    - override register and *optional _translate_event method

    '''

    type = 'Event'

    def __init__(self, session, plugins_presets={}):
        '''Expects a ftrack_api.Session instance'''
        super().__init__(session, plugins_presets)

    # Decorator
    def launch_log(self, func):
        @functools.wraps(func)
        def wrapper_launch(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception as exc:
                self.session.rollback()
                self.log.error(
                    'Event "{}" Failed: {}'.format(
                        self.__class__.__name__, str(exc)
                    ),
                    exc_info=True
                )
        return wrapper_launch

    def register(self):
        '''Registers the event, subscribing the discover and launch topics.'''
        self.session.event_hub.subscribe(
            'topic=ftrack.update',
            self._launch,
            priority=self.priority
        )

    def _translate_event(self, event, session=None):
        '''Return *event* translated structure to be used with the API.'''
        return self._get_entities(
            event,
            session,
            ignore=['socialfeed', 'socialnotification']
        )
