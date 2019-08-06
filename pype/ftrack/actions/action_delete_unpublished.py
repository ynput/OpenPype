import sys
import argparse
import logging
from pype.vendor import ftrack_api
from pype.ftrack import BaseAction


class VersionsCleanup(BaseAction):
    '''Custom action.'''

    # Action identifier
    identifier = 'versions.cleanup'
    # Action label
    label = 'Versions cleanup'

    def discover(self, session, entities, event):
        ''' Validation '''

        # Only 1 AssetVersion is allowed
        if len(entities) != 1 or entities[0].entity_type != 'AssetVersion':
            return False

        return True

    def launch(self, session, entities, event):

        entity = entities[0]

        # Go through all versions in asset
        for version in entity['asset']['versions']:
            if not version['is_published']:
                session.delete(version)
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise

        return {
            'success': True,
            'message': 'Hidden versions were removed'
        }


def register(session, **kw):
    '''Register action. Called when used as an event plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    VersionsCleanup(session).register()


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
