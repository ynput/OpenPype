import sys
import argparse
import logging
from pype.vendor import ftrack_api
from pype.ftrack import BaseAction


class AssetDelete(BaseAction):
    '''Custom action.'''

    #: Action identifier.
    identifier = 'asset.delete'
    #: Action label.
    label = 'Asset Delete'

    def discover(self, session, entities, event):
        ''' Validation '''

        if (
            len(entities) != 1 or
            entities[0].entity_type not in ['Shot', 'Asset Build']
        ):
            return False

        return True

    def interface(self, session, entities, event):

        if not event['data'].get('values', {}):
            entity = entities[0]

            items = []
            for asset in entity['assets']:
                # get asset name for label
                label = 'None'
                if asset['name']:
                    label = asset['name']

                items.append({
                    'label': label,
                    'name': label,
                    'value': False,
                    'type': 'boolean'
                })

            if len(items) < 1:
                return {
                    'success': False,
                    'message': 'There are no assets to delete'
                }

            return items

    def launch(self, session, entities, event):

        entity = entities[0]
        # if values were set remove those items
        if 'values' in event['data']:
            values = event['data']['values']
            # get list of assets to delete from form
            to_delete = []
            for key in values:
                if values[key]:
                    to_delete.append(key)
            # delete them by name
            for asset in entity['assets']:
                if asset['name'] in to_delete:
                    session.delete(asset)
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise

        return {
            'success': True,
            'message': 'Asset deleted.'
        }


def register(session, plugins_presets={}):
    '''Register action. Called when used as an event plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    AssetDelete(session, plugins_presets).register()


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
