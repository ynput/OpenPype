# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

import logging

import ftrack_api
import ftrack_api.entity.location
import ftrack_api.accessor.disk


def configure_locations(event):
    '''Configure locations for session.'''
    session = event['data']['session']

    # Find location(s) and customise instances.
    #
    # location = session.query('Location where name is "my.location"').one()
    # ftrack_api.mixin(location, ftrack_api.entity.location.UnmanagedLocationMixin)
    # location.accessor = ftrack_api.accessor.disk.DiskAccessor(prefix='')


def register(session):
    '''Register plugin with *session*.'''
    logger = logging.getLogger('ftrack_plugin:configure_locations.register')

    # Validate that session is an instance of ftrack_api.Session. If not, assume
    # that register is being called from an old or incompatible API and return
    # without doing anything.
    if not isinstance(session, ftrack_api.Session):
        logger.debug(
            'Not subscribing plugin as passed argument {0} is not an '
            'ftrack_api.Session instance.'.format(session)
        )
        return

    session.event_hub.subscribe(
        'topic=ftrack.api.session.configure-location',
        configure_locations
    )
