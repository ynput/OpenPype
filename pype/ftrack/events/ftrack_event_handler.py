# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack
import os
import logging
import getpass
# import platform
import ftrack_api
import toml
from avalon import io, lib, pipeline
from avalon import session as sess
import acre

from app.api import (
    Templates,
    Logger
)


class BaseEvent(object):
    '''Custom Action base class

    `label` a descriptive string identifing your action.

    `varaint` To group actions together, give them the same
    label and specify a unique variant per action.

    `identifier` a unique identifier for your action.

    `description` a verbose descriptive text for you action

     '''

    def __init__(self, session):
        '''Expects a ftrack_api.Session instance'''

        self.log = Logger.getLogger(self.__class__.__name__)

        self._session = session

    @property
    def session(self):
        '''Return current session.'''
        return self._session

    def register(self):
        '''Registers the event, subscribing the the discover and launch topics.'''
        self.session.event_hub.subscribe('topic=ftrack.update', self._launch)

        self.log.info("----- event - <" + self.__class__.__name__ + "> - Has been registered -----")

    def _translate_event(self, session, event):
        '''Return *event* translated structure to be used with the API.'''
        _selection = event['data'].get('entities',[])

        _entities = list()
        for entity in _selection:
            if entity['entityType'] in ['socialfeed']:
                continue
            _entities.append(
                (
                    session.get(self._get_entity_type(entity), entity.get('entityId'))
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

        # TODO REMOVE THIS - ONLY FOR TEST PROJECT
        for a in args[0]:
            try:
                if (a['project']['name'] != 'eventproj'):
                    return True
            except:
                continue

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

    def show_message(self, event, input_message, result = False):
        if not isinstance(result, bool):
            result = False

        try:
            message = str(input_message)
        except:
            return
        source = {}
        source['id'] = event['source']['applicationId']
        source['user'] = event['source']['user']
        self.session.event_hub.publish_reply(event, event['data'], source)
        # event = ftrack_api.event.base.Event(
        #     topic='show_message_topic',
        #     data={'success':result, 'message': message}
        # )
        #
        # self.session.event_hub.publish(event)

    def _handle_result(self, session, result, entities, event):
        '''Validate the returned result from the action callback'''
        if isinstance(result, bool):
            result = {
                'success': result,
                'message': (
                    '{0} launched successfully.'.format(
                        self.__class__.__name__
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
