# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack
import sys
import argparse
import logging
import collections
import os
import json

import ftrack_api
from ftrack_action_handler.action import BaseAction
from avalon import io, inventory, schema
from avalon.vendor import toml


class TestAction(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'test.action'

    #: Action label.
    label = 'Test action'

    #: Action description.
    description = 'Test action'

    def validate_selection(self, session, entities):
        '''Return if *entities* is a valid selection.'''
        pass
        return True

    def discover(self, session, entities, event):
        '''Return True if action is valid.'''

        self.logger.info('Got selection: {0}'.format(entities))
        return self.validate_selection(session, entities)

    def launch(self, session, entities, event):
        
        return True


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = TestAction(session)
    action_handler.register()


def main(arguments=None):
    '''Set up logging and register action.'''
    if arguments is None:
        arguments = []

    parser = argparse.ArgumentParser()
    # Allow setting of logging level from arguments.
    loggingLevels = {}
    for level in (
        logging.NOTSET, logging.DEBUG, logging.INFO, logging.WARNING,
        logging.ERROR, logging.CRITICAL
    ):
        loggingLevels[logging.getLevelName(level).lower()] = level

    parser.add_argument(
        '-v', '--verbosity',
        help='Set the logging output verbosity.',
        choices=loggingLevels.keys(),
        default='info'
    )
    namespace = parser.parse_args(arguments)

    # Set up basic logging
    logging.basicConfig(level=loggingLevels[namespace.verbosity])

    session = ftrack_api.Session(
        server_url="https://pype.ftrackapp.com",
        api_key="4e01eda0-24b3-4451-8e01-70edc03286be",
        api_user="jakub.trllo"
    )
    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
