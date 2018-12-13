# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack
import sys
import argparse
import logging
import collections
import os
import json
import re

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
        discover = False
        roleList = ['Pypeclub']
        userId = event['source']['user']['id']
        user = session.query('User where id is ' + userId).one()

        for role in user['user_security_roles']:
            if role['security_role']['name'] in roleList:
                discover = True
                break

        return discover


    def launch(self, session, entities, event):
        entity = entities[0]


        entity_type = entity.entity_type
        data = {}
        """
        custom_attributes = []

        all_avalon_attr = session.query('CustomAttributeGroup where name is "avalon"').one()
        for cust_attr in all_avalon_attr['custom_attribute_configurations']:
            if 'avalon_' not in cust_attr['key']:
                custom_attributes.append(cust_attr)
        """
        for cust_attr in custom_attributes:
            if cust_attr['entity_type'].lower() in ['asset']:
                data[cust_attr['key']] = entity['custom_attributes'][cust_attr['key']]

            elif cust_attr['entity_type'].lower() in ['show'] and entity_type.lower() == 'project':
                data[cust_attr['key']] = entity['custom_attributes'][cust_attr['key']]

            elif cust_attr['entity_type'].lower() in ['task'] and entity_type.lower() != 'project':
                # Put space between capitals (e.g. 'AssetBuild' -> 'Asset Build')
                entity_type = re.sub(r"(\w)([A-Z])", r"\1 \2", entity_type)
                # Get object id of entity type
                ent_obj_type_id = session.query('ObjectType where name is "{}"'.format(entity_type)).one()['id']
                if cust_attr['type_id'] == ent_obj_type_id:
                    data[cust_attr['key']] = entity['custom_attributes'][cust_attr['key']]

        return True


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = TestAction(session)
    action_handler.register(10000)


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
