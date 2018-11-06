# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack
import sys
import argparse
import logging
import collections
import os
import json

import ftrack_api
from ftrack_action_handler import BaseAction
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


    def discover(self, session, entities, event):
        ''' Validation '''

        return True


    def launch(self, session, entities, event):

        for entity in entities:
            index = 0
            name = entity['components'][index]['name']
            filetype = entity['components'][index]['file_type']
            path = entity['components'][index]['component_locations'][0]['resource_identifier']

            # entity['components'][index]['component_locations'][0]['resource_identifier'] = r"C:\Users\jakub.trllo\Desktop\test\exr\int_c022_lighting_v001_main_AO.%04d.exr"
            location = entity['components'][0]['component_locations'][0]['location']
            component = entity['components'][0]


            # print(location.get_filesystem_path(component))

            # for k in p:
            #     print(100*"-")
            #     print(k)
            #     print(p[k])

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

    session = ftrack_api.Session()
    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
