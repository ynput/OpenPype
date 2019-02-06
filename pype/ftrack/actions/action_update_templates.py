import sys
import argparse
import logging

import ftrack_api
from pype.ftrack import BaseAction
from avalon import io
import pype

ignore_me = True


class UpdateTemplates(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'update.templates'
    #: Action label.
    label = 'UpdateTemplates'
    #: Action description.
    description = 'Updates templates in project'
    #: priority
    priority = 10000

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
        anatomy = pype.Anatomy
        io.install()
        for project in io.projects():
            io.Session["AVALON_PROJECT"] = project["name"]
            io.update_many(
                {'type': 'project'},
                {'$set': {
                    'config.template.workfile': anatomy.avalon.workfile,
                    'config.template.work': anatomy.avalon.work,
                    'config.template.publish': anatomy.avalon.publish,
                }}
            )

            io.update_many(
                {'type': 'representation'},
                {'$set': {
                    'data.template': anatomy.avalon.publish
                }}
            )

        return True


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = UpdateTemplates(session)
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
