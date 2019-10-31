import os
import sys
import logging
from bson.objectid import ObjectId
import argparse
from pype.vendor import ftrack_api
from pype.ftrack import BaseAction
from pype.ftrack.lib.io_nonsingleton import DbConnector


class DeleteAsset(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'delete.asset'
    #: Action label.
    label = 'Delete Asset/Subsets'
    #: Action description.
    description = 'Removes from Avalon with all childs and asset from Ftrack'
    icon = '{}/ftrack/action_icons/DeleteAsset.svg'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )
    #: roles that are allowed to register this action
    role_list = ['Pypeclub', 'Administrator']
    #: Db
    db = DbConnector()

    value = None

    def discover(self, session, entities, event):
        ''' Validation '''
        if len(entities) != 1:
            return False

        valid = ["task"]
        entityType = event["data"]["selection"][0].get("entityType", "")
        if entityType.lower() not in valid:
            return False

        return True

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

            confirmation = self.confirm_delete(
                True, *args
            )

            if interface:
                return interface

            if confirmation:
                return confirmation

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
            self.attempt = 1
            items = []
            entity = entities[0]
            title = 'Choose items to delete from "{}"'.format(entity['name'])
            project = entity['project']

            self.db.Session['AVALON_PROJECT'] = project["full_name"]

            av_entity = self.db.find_one({
                'type': 'asset',
                'name': entity['name']
            })

            if av_entity is None:
                return {
                    'success': False,
                    'message': 'Didn\'t found assets in avalon'
                }

            asset_label = {
                'type': 'label',
                'value': '## Delete whole asset: ##'
            }
            asset_item = {
                'label': av_entity['name'],
                'name': 'whole_asset',
                'type': 'boolean',
                'value': False
            }
            splitter = {
                'type': 'label',
                'value': '{}'.format(200*"-")
            }
            subset_label = {
                'type': 'label',
                'value': '## Subsets: ##'
            }
            if av_entity is not None:
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

    def confirm_delete(self, first_attempt, entities, event):
        if first_attempt is True:
            if 'values' not in event['data']:
                return

            values = event['data']['values']

            if len(values) <= 0:
                return
            if 'whole_asset' not in values:
                return
        else:
            values = self.values

        title = 'Confirmation of deleting {}'
        if values['whole_asset'] is True:
            title = title.format(
                'whole asset {}'.format(
                    entities[0]['name']
                )
            )
        else:
            subsets = []
            for key, value in values.items():
                if value is True:
                    subsets.append(key)
            len_subsets = len(subsets)
            if len_subsets == 0:
                return {
                    'success': True,
                    'message': 'Nothing was selected to delete'
                }
            elif len_subsets == 1:
                title = title.format(
                    '{} subset'.format(len_subsets)
                )
            else:
                title = title.format(
                    '{} subsets'.format(len_subsets)
                )

        self.values = values
        items = []

        delete_label = {
            'type': 'label',
            'value': '# Please enter "DELETE" to confirm #'
        }

        delete_item = {
            'name': 'delete_key',
            'type': 'text',
            'value': '',
            'empty_text': 'Type Delete here...'
        }
        items.append(delete_label)
        items.append(delete_item)

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
        if 'delete_key' not in values:
            return

        if values['delete_key'].lower() != 'delete':
            if values['delete_key'].lower() == '':
                return {
                    'success': False,
                    'message': 'Deleting cancelled'
                }
            if self.attempt < 3:
                self.attempt += 1
                return_dict = self.confirm_delete(False, entities, event)
                return_dict['title'] = '{} ({} attempt)'.format(
                    return_dict['title'], self.attempt
                )
                return return_dict
            return {
                'success': False,
                'message': 'You didn\'t enter "DELETE" properly 3 times!'
            }

        entity = entities[0]
        project = entity['project']

        self.db.Session['AVALON_PROJECT'] = project["full_name"]

        all_ids = []
        if self.values.get('whole_asset', False) is True:
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
            subset_names = []
            for key, value in self.values.items():
                if key == 'delete_key' or value is False:
                    continue

                entity_id = ObjectId(key)
                av_entity = self.db.find_one({'_id': entity_id})
                subset_names.append(av_entity['name'])
                if av_entity is None:
                    continue
                all_ids.append(entity_id)
                all_ids.extend(self.find_child(av_entity))

            for ft_asset in entity['assets']:
                if ft_asset['name'] in subset_names:
                    session.delete(ft_asset)
                    session.commit()

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


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    DeleteAsset(session, plugins_presets).register()


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
