# :coding: utf-8
import logging

import ftrack_api.session


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

    # Perform your logic here, such as subscribe to an event.
    pass

    logger.debug('Plugin registered')
