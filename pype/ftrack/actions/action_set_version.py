import sys
import argparse
import logging
from pype.vendor import ftrack_api
from pype.ftrack import BaseAction


class SetVersion(BaseAction):
    '''Custom action.'''

    #: Action identifier.
    identifier = 'version.set'
    #: Action label.
    label = 'Version Set'

    def discover(self, session, entities, event):
        ''' Validation '''

        # Only 1 AssetVersion is allowed
        if len(entities) != 1 or entities[0].entity_type != 'AssetVersion':
            return False

        return True

    def interface(self, session, entities, event):

        if not event['data'].get('values', {}):
            entity = entities[0]

            # Get actual version of asset
            act_ver = entity['version']
            # Set form
            items = [{
                'label': 'Version number',
                'type': 'number',
                'name': 'version_number',
                'value': act_ver
            }]

            return items

    def launch(self, session, entities, event):

        entity = entities[0]

        # Do something with the values or return a new form.
        values = event['data'].get('values', {})
        # Default is action True
        scs = False

        if not values['version_number']:
            msg = 'You didn\'t enter any version.'
        elif int(values['version_number']) <= 0:
            msg = 'Negative or zero version is not valid.'
        else:
            try:
                entity['version'] = values['version_number']
                session.commit()
                msg = 'Version was changed to v{0}'.format(
                    values['version_number']
                )
                scs = True
            except Exception as e:
                msg = 'Unexpected error occurs during version set ({})'.format(
                    str(e)
                )

        return {
            'success': scs,
            'message': msg
        }


def register(session, **kw):
    '''Register action. Called when used as an event plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    SetVersion(session).register()


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
