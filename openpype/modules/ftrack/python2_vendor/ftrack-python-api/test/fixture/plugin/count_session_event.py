# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack
import logging
import collections

import ftrack_api.session


def count_session_event(event):
    '''Called when session is ready to be used.'''
    logger = logging.getLogger('com.ftrack.test-session-event-plugin')
    event_topic = event['topic']
    logger.debug(u'Event received: {}'.format(event_topic))
    session = event['data']['session']
    session._test_called_events[event_topic] += 1


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''
    logger = logging.getLogger('com.ftrack.test-session-event-plugin')

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        logger.debug(
            'Not subscribing plugin as passed argument {0!r} is not an '
            'ftrack_api.Session instance.'.format(session)
        )
        return

    session._test_called_events = collections.defaultdict(int)
    session.event_hub.subscribe(
        'topic=ftrack.api.session.ready',
        count_session_event
    )
    session.event_hub.subscribe(
        'topic=ftrack.api.session.reset',
        count_session_event
    )
    logger.debug('Plugin registered')
