import os
import sys
import argparse
import logging
import collections
import json
import re

import ftrack_api
from avalon import io, inventory, schema
from pype.modules.ftrack import BaseAction


class TestAction(BaseAction):
    '''Edit meta data action.'''

    ignore_me = True
    #: Action identifier.
    identifier = 'test.action'
    #: Action label.
    label = 'Test action'
    #: Action description.
    description = 'Test action'
    #: priority
    priority = 10000
    #: roles that are allowed to register this action
    role_list = ['Pypeclub']
    icon = '{}/ftrack/action_icons/TestAction.svg'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )

    def discover(self, session, entities, event):
        ''' Validation '''

        return True

    def launch(self, session, entities, event):
        self.log.info(event)

        return True


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    TestAction(session, plugins_presets).register()


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

    session = ftrack_api.Session()
    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
