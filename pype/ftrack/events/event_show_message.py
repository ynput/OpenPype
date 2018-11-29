import os
import sys
import re
import ftrack_api
from ftrack_event_handler import BaseEvent
from app import api

class Show_Message(BaseEvent):

    def launch(self, event):

        self.session.event_hub.publish_reply(event, event['data'])
        return event['data']

    def register(self):
        # self.session.event_hub.subscribe('topic=show_message_topic', self.launch)

        self.session.event_hub.subscribe(
            'topic=ftrack.action.launch and data.actionIdentifier={0} and source.user.username={1}'.format(
                self.identifier,
                self.session.api_user
            ),
            self._launch
        )

def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''
    if not isinstance(session, ftrack_api.session.Session):
        return

    event = Show_Message(session)
    event.register()
