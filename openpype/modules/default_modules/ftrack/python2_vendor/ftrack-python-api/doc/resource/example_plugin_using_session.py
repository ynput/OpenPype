# :coding: utf-8
import logging

import ftrack_api.session


def register_with_session_ready(event):
    '''Called when session is ready to be used.'''
    logger = logging.getLogger('com.example.example-plugin')
    logger.debug('Session ready.')
    session = event['data']['session']

    # Session is now ready and can be used to e.g. query objects.
    task = session.query('Task').first()
    print task['name']


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''
    logger = logging.getLogger('com.example.example-plugin')

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        logger.debug(
            'Not subscribing plugin as passed argument {0!r} is not an '
            'ftrack_api.Session instance.'.format(session)
        )
        return

    session.event_hub.subscribe(
        'topic=ftrack.api.session.ready',
        register_with_session_ready
    )

    logger.debug('Plugin registered')
