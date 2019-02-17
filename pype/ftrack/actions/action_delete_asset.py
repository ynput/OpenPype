import sys
import logging
import random
import string
import argparse
import ftrack_api
from pype.ftrack import BaseAction
from avalon.tools.libraryloader.io_nonsingleton import DbConnector


class DeleteEntity(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'delete.entity'
    #: Action label.
    label = 'Delete entity'
    #: Action description.
    description = 'Removes assets from Ftrack and Avalon db with all childs'
    icon = "https://www.iconsdb.com/icons/preview/white/full-trash-xxl.png"
    #: Db
    db = DbConnector()

    def discover(self, session, entities, event):
        ''' Validation '''
        selection = event["data"].get("selection", None)
        if selection is None or len(selection) > 1:
            return False

        valid = ["task"]
        entityType = selection[0].get("entityType", "")
        if entityType.lower() not in valid:
            return False

        discover = False
        roleList = ['Pypeclub', 'Administrator']
        userId = event['source']['user']['id']
        user = session.query('User where id is ' + userId).one()

        for role in user['user_security_roles']:
            if role['security_role']['name'] in roleList:
                discover = True
                break

        return discover

    def interface(self, session, entities, event):
        if not event['data'].get('values', {}):
            entity = entities[0]
            title = 'Going to delete "{}"'.format(entity['name'])

            items = []
            item = {
                'label': 'Enter "DELETE" to confirm',
                'name': 'key',
                'type': 'text',
                'value': ''
            }
            items.append(item)

            return {
                'items': items,
                'title': title
            }

    def launch(self, session, entities, event):
        if 'values' not in event['data']:
            return

        values = event['data']['values']
        if len(values) <= 0:
            return {
                'success': True,
                'message': 'No Assets to delete!'
            }
        elif values.get('key', '').lower() != 'delete':
            return {
                'success': False,
                'message': 'Entered key does not match'
            }
        entity = entities[0]
        project = entity['project']

        self.db.install()
        self.db.Session['AVALON_PROJECT'] = project["full_name"]

        av_entity = self.db.find_one({
            'type': 'asset',
            'name': entity['name']
        })

        if av_entity is not None:
            all_ids = []
            all_ids.append(av_entity['_id'])
            all_ids.extend(self.find_child(av_entity))

            if len(all_ids) == 0:
                self.db.uninstall()
                return {
                    'success': True,
                    'message': 'None of assets'
                }

            or_subquery = []
            for id in all_ids:
                or_subquery.append({'_id': id})
            delete_query = {'$or': or_subquery}
            self.db.delete_many(delete_query)

        session.delete(entity)
        session.commit()
        self.db.uninstall()

        return {
            'success': True,
            'message': 'All assets were deleted!'
        }

    def find_child(self, entity):
        output = []
        id = entity['_id']
        visuals = [x for x in self.db.find({'data.visualParent': id})]
        assert len(visuals) == 0, 'This asset has another asset as child'
        childs = self.db.find({'parent': id})
        for child in childs:
            output.append(child['_id'])
            output.extend(self.find_child(child))
        return output

    def find_assets(self, asset_names):
        assets = []
        for name in asset_names:
            entity = self.db.find_one({
                'type': 'asset',
                'name': name
            })
            if entity is not None and entity not in assets:
                assets.append(entity)
        return assets


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = DeleteEntity(session)
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
