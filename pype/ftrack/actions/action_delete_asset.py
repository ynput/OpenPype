import sys
import logging
from bson.objectid import ObjectId
import argparse
import ftrack_api
from pype.ftrack import BaseAction
from avalon.tools.libraryloader.io_nonsingleton import DbConnector


class DeleteAsset(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'delete.asset'
    #: Action label.
    label = 'Delete asset/subsets'
    #: Action description.
    description = 'Removes from Avalon with all childs and asset from Ftrack'
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

    def _launch(self, event):
        self.reset_session()
        try:
            self.db.install()
            args = self._translate_event(
                self.session, event
            )

            interface = self._interface(
                self.session, *args
            )

            if interface:
                return interface

            response = self.launch(
                self.session, *args
            )
        finally:
            self.db.uninstall()

        return self._handle_result(
            self.session, response, *args
        )

    def interface(self, session, entities, event):
        if not event['data'].get('values', {}):
            items = []
            entity = entities[0]
            title = 'Choose items to delete from "{}"'.format(entity['name'])
            project = entity['project']

            self.db.Session['AVALON_PROJECT'] = project["full_name"]

            av_entity = self.db.find_one({
                'type': 'asset',
                'name': entity['name']
            })

            asset_label = {
                'type': 'label',
                'value': '*Delete whole asset:*'
            }
            asset_item = {
                'label': av_entity['name'],
                'name': 'whole_asset',
                'type': 'boolean',
                'value': False
            }
            delete_item = {
                'label': 'Enter "DELETE" to confirm',
                'name': 'delete_key',
                'type': 'text',
                'value': ''
            }
            splitter = {
                'type': 'label',
                'value': '{}'.format(200*"-")
            }
            subset_label = {
                'type': 'label',
                'value': '*Subsets:*'
            }
            if av_entity is not None:
                items.append(delete_item)
                items.append(splitter)
                items.append(asset_label)
                items.append(asset_item)
                items.append(splitter)

                all_subsets = self.db.find({
                    'type': 'subset',
                    'parent': av_entity['_id']
                })

                subset_items = []
                for subset in all_subsets:
                    item = {
                        'label': subset['name'],
                        'name': str(subset['_id']),
                        'type': 'boolean',
                        'value': False
                    }
                    subset_items.append(item)
                if len(subset_items) > 0:
                    items.append(subset_label)
                    items.extend(subset_items)
            else:
                return {
                    'success': False,
                    'message': 'Didn\'t found assets in avalon'
                }

            return {
                'items': items,
                'title': title
            }

    def launch(self, session, entities, event):
        if 'values' not in event['data']:
            return

        values = event['data']['values']
        if len(values) <= 0:
            return
        elif values.get('delete_key', '').lower() != 'delete':
            return {
                'success': False,
                'message': 'You didn\'t enter "DELETE" properly!'
            }

        entity = entities[0]
        project = entity['project']

        self.db.Session['AVALON_PROJECT'] = project["full_name"]

        all_ids = []
        if values.get('whole_asset', False) is True:
            av_entity = self.db.find_one({
                'type': 'asset',
                'name': entity['name']
            })

            if av_entity is not None:
                all_ids.append(av_entity['_id'])
                all_ids.extend(self.find_child(av_entity))

            session.delete(entity)
            session.commit()
        else:
            for key, value in values.items():
                if key == 'delete_key' or value is False:
                    continue

                entity_id = ObjectId(key)
                av_entity = self.db.find_one({'_id': entity_id})
                if av_entity is None:
                    continue
                all_ids.append(entity_id)
                all_ids.extend(self.find_child(av_entity))

        if len(all_ids) == 0:
            return {
                'success': True,
                'message': 'No entities to delete in avalon'
            }

        or_subquery = []
        for id in all_ids:
            or_subquery.append({'_id': id})
        delete_query = {'$or': or_subquery}
        self.db.delete_many(delete_query)

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

    DeleteAsset(session).register()


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
