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

    def get_project_name_from_event(self, session, event, project_id):
        """Load or query and fill project entity from/to event data.

        Project data are stored by ftrack id because in most cases it is
        easier to access project id than project name.

        Args:
            session (ftrack_api.Session): Current session.
            event (ftrack_api.Event): Processed event by session.
            project_id (str): Ftrack project id.
        """
        if not project_id:
            raise ValueError(
                "Entered `project_id` is not valid. {} ({})".format(
                    str(project_id), str(type(project_id))
                )
            )
        # Try to get project entity from event
        project_data = event["data"].get("project_data")
        if not project_data:
            project_data = {}
            event["data"]["project_data"] = project_data

        project_name = project_data.get(project_id)
        if not project_name:
            # Get project entity from task and store to event
            project_entity = session.get("Project", project_id)
            project_name = project_entity["full_name"]
            event["data"]["project_data"][project_id] = project_name
        return project_name
