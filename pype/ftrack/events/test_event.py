import os
import sys
import re
import ftrack_api
from ftrack_event_handler import BaseEvent
from app import api

class Test_Event(BaseEvent):

    def launch(self, session, entities, event):

        '''just a testing event'''
        result = True
        message = "test message"
        data = {
            'success':result,
            'message': message,
        }

        self.log.info(event['data']['entities'])
        # event['source']['id']


        # self.session.event_hub.publish_reply(event, data, subscriber.metadata)

        # subscriber = None
        # self.log.info("before Message")
        # for s in self.session.event_hub._subscribers:
        #     if 'topic=custom_message_show' == str(s.subscription):
        #         subscriber = s
        #         break
        #
        # if subscriber is not None:
        #     id = subs.metadata['id']
        #
        #     event = ftrack_api.event.base.Event(
        #     topic='topic=custom_message_show',
        #     data=data
        #     )
        #     self.session.event_hub.publish(event)
        # self.log.info("after Message")
        # self.show_message(event,"Test",True)
        # self.log.info(event['source'])
        return True


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''
    if not isinstance(session, ftrack_api.session.Session):
        return

    event = Test_Event(session)
    event.register()

# <Event {
#     'id': '2c6fc29e4ae342adbdf9eb8055759bd5',
#     'data': {
#         'entities': [
#             {
#                 'keys': ['name'],
#                 'objectTypeId': '4be63b64-5010-42fb-bf1f-428af9d638f0',
#                 'entityType': 'task',
#                 'parents': [
#                     {'entityId': '42cb361a-f25b-11e8-b54e-0a580aa00143', 'entityType': 'task', 'parentId': '682ed692-f246-11e8-871e-0a580aa00143'},
#                     {'entityId': '682ed692-f246-11e8-871e-0a580aa00143', 'entityType': 'task', 'parentId': '2b7a3e24-f185-11e8-ac34-0a580aa00143'},
#                     {'entityId': '2b7a3e24-f185-11e8-ac34-0a580aa00143', 'entityType': 'show', 'parentId': None}],
#                 'parentId': '682ed692-f246-11e8-871e-0a580aa00143',
#                 'action': 'update',
#                 'entityId': '42cb361a-f25b-11e8-b54e-0a580aa00143',
#                 'changes': {'name': {'new': 'Cat01', 'old': 'Cat0'}}}],
#                 'pushToken': 'b2e8d89ef3d711e899120a580aa00143',
#                 'parents': ['682ed692-f246-11e8-871e-0a580aa00143', '42cb361a-f25b-11e8-b54e-0a580aa00143', '2b7a3e24-f185-11e8-ac34-0a580aa00143'],
#                 'user': {'userid': '2a8ae090-cbd3-11e8-a87a-0a580aa00121', 'name': 'Kuba Trllo'},
#                 'clientToken': 'b1e10dcc-f3d7-11e8-a9de-0a580aa00143'},
#                 'topic': 'ftrack.update',
#                 'sent': None,
#                 'source': {
#                     'applicationId': 'ftrack.client.web',
#                     'user': {'username': 'jakub.trllo', 'id': '2a8ae090-cbd3-11e8-a87a-0a580aa00121'},
#                     'id': 'b1e10dcc-f3d7-11e8-a9de-0a580aa00143'},
#                 'target': '',
#                 'in_reply_to_event': None}>]
