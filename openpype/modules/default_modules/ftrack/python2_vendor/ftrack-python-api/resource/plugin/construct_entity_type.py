# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

import logging

import ftrack_api.entity.factory


class Factory(ftrack_api.entity.factory.StandardFactory):
    '''Entity class factory.'''

    def create(self, schema, bases=None):
        '''Create and return entity class from *schema*.'''
        # Optionally change bases for class to be generated.
        cls = super(Factory, self).create(schema, bases=bases)

        # Further customise cls before returning.

        return cls


def register(session):
    '''Register plugin with *session*.'''
    logger = logging.getLogger('ftrack_plugin:construct_entity_type.register')

    # Validate that session is an instance of ftrack_api.Session. If not, assume
    # that register is being called from an old or incompatible API and return
    # without doing anything.
    if not isinstance(session, ftrack_api.Session):
        logger.debug(
            'Not subscribing plugin as passed argument {0!r} is not an '
            'ftrack_api.Session instance.'.format(session)
        )
        return

    factory = Factory()

    def construct_entity_type(event):
        '''Return class to represent entity type specified by *event*.'''
        schema = event['data']['schema']
        return factory.create(schema)

    session.event_hub.subscribe(
        'topic=ftrack.api.session.construct-entity-type',
        construct_entity_type
    )
