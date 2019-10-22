import os
import sys
import json
import argparse
import logging
import collections

from pype.vendor import ftrack_api
from pype.ftrack import BaseAction, lib
from pype.ftrack.lib.io_nonsingleton import DbConnector
from bson.objectid import ObjectId


class SyncHierarchicalAttrs(BaseAction):

    db_con = DbConnector()
    ca_mongoid = lib.get_ca_mongoid()

    #: Action identifier.
    identifier = 'sync.hierarchical.attrs.local'
    #: Action label.
    label = "Pype Admin"
    variant = '- Sync Hier Attrs (Local)'
    #: Action description.
    description = 'Synchronize hierarchical attributes'
    #: Icon
    icon = '{}/ftrack/action_icons/PypeAdmin.svg'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )

    #: roles that are allowed to register this action
    role_list = ['Pypeclub', 'Administrator', 'Project Manager']

    def discover(self, session, entities, event):
        ''' Validation '''
        for entity in entities:
            if (
                entity.get('context_type', '').lower() in ('show', 'task') and
                entity.entity_type.lower() != 'task'
            ):
                return True
        return False

    def launch(self, session, entities, event):
        self.interface_messages = {}
        user = session.query(
            'User where id is "{}"'.format(event['source']['user']['id'])
        ).one()

        job = session.create('Job', {
            'user': user,
            'status': 'running',
            'data': json.dumps({
                'description': 'Sync Hierachical attributes'
            })
        })
        session.commit()
        self.log.debug('Job with id "{}" created'.format(job['id']))

        process_session = ftrack_api.Session(
            server_url=session.server_url,
            api_key=session.api_key,
            api_user=session.api_user,
            auto_connect_event_hub=True
        )

        try:
            # Collect hierarchical attrs
            self.log.debug('Collecting Hierarchical custom attributes started')
            custom_attributes = {}
            all_avalon_attr = process_session.query(
                'CustomAttributeGroup where name is "avalon"'
            ).one()

            error_key = (
                'Hierarchical attributes with set "default" value (not allowed)'
            )

            for cust_attr in all_avalon_attr['custom_attribute_configurations']:
                if 'avalon_' in cust_attr['key']:
                    continue

                if not cust_attr['is_hierarchical']:
                    continue

                if cust_attr['default']:
                    if error_key not in self.interface_messages:
                        self.interface_messages[error_key] = []
                    self.interface_messages[error_key].append(
                        cust_attr['label']
                    )

                    self.log.warning((
                        'Custom attribute "{}" has set default value.'
                        ' This attribute can\'t be synchronized'
                    ).format(cust_attr['label']))
                    continue

                custom_attributes[cust_attr['key']] = cust_attr

            self.log.debug(
                'Collecting Hierarchical custom attributes has finished'
            )

            if not custom_attributes:
                msg = 'No hierarchical attributes to sync.'
                self.log.debug(msg)
                return {
                    'success': True,
                    'message': msg
                }

            entity = entities[0]
            if entity.entity_type.lower() == 'project':
                project_name = entity['full_name']
            else:
                project_name = entity['project']['full_name']

            self.db_con.install()
            self.db_con.Session['AVALON_PROJECT'] = project_name

            _entities = self._get_entities(event, process_session)

            for entity in _entities:
                self.log.debug(30*'-')
                self.log.debug(
                    'Processing entity "{}"'.format(entity.get('name', entity))
                )

                ent_name = entity.get('name', entity)
                if entity.entity_type.lower() == 'project':
                    ent_name = entity['full_name']

                for key in custom_attributes:
                    self.log.debug(30*'*')
                    self.log.debug(
                        'Processing Custom attribute key "{}"'.format(key)
                    )
                    # check if entity has that attribute
                    if key not in entity['custom_attributes']:
                        error_key = 'Missing key on entities'
                        if error_key not in self.interface_messages:
                            self.interface_messages[error_key] = []

                        self.interface_messages[error_key].append(
                            '- key: "{}" - entity: "{}"'.format(key, ent_name)
                        )

                        self.log.error((
                            '- key "{}" not found on "{}"'
                        ).format(key, ent_name))
                        continue

                    value = self.get_hierarchical_value(key, entity)
                    if value is None:
                        error_key = (
                            'Missing value for key on entity'
                            ' and its parents (synchronization was skipped)'
                        )
                        if error_key not in self.interface_messages:
                            self.interface_messages[error_key] = []

                        self.interface_messages[error_key].append(
                            '- key: "{}" - entity: "{}"'.format(key, ent_name)
                        )

                        self.log.warning((
                            '- key "{}" not set on "{}" or its parents'
                        ).format(key, ent_name))
                        continue

                    self.update_hierarchical_attribute(entity, key, value)

            job['status'] = 'done'
            session.commit()

        except Exception:
            self.log.error(
                'Action "{}" failed'.format(self.label),
                exc_info=True
            )

        finally:
            self.db_con.uninstall()

            if job['status'] in ('queued', 'running'):
                job['status'] = 'failed'
            session.commit()
            if self.interface_messages:
                title = "Errors during SyncHierarchicalAttrs"
                self.show_interface_from_dict(
                    messages=self.interface_messages, title=title, event=event
                )

        return True

    def get_hierarchical_value(self, key, entity):
        value = entity['custom_attributes'][key]
        if (
            value is not None or
            entity.entity_type.lower() == 'project'
        ):
            return value

        return self.get_hierarchical_value(key, entity['parent'])

    def update_hierarchical_attribute(self, entity, key, value):
        if (
            entity['context_type'].lower() not in ('show', 'task') or
            entity.entity_type.lower() == 'task'
        ):
            return

        ent_name = entity.get('name', entity)
        if entity.entity_type.lower() == 'project':
            ent_name = entity['full_name']

        hierarchy = '/'.join(
            [a['name'] for a in entity.get('ancestors', [])]
        )
        if hierarchy:
            hierarchy = '/'.join(
                [entity['project']['full_name'], hierarchy, entity['name']]
            )
        elif entity.entity_type.lower() == 'project':
            hierarchy = entity['full_name']
        else:
            hierarchy = '/'.join(
                [entity['project']['full_name'], entity['name']]
            )

        self.log.debug('- updating entity "{}"'.format(hierarchy))

        # collect entity's custom attributes
        custom_attributes = entity.get('custom_attributes')
        if not custom_attributes:
            return

        mongoid = custom_attributes.get(self.ca_mongoid)
        if not mongoid:
            error_key = 'Missing MongoID on entities (try SyncToAvalon first)'
            if error_key not in self.interface_messages:
                self.interface_messages[error_key] = []

            if ent_name not in self.interface_messages[error_key]:
                self.interface_messages[error_key].append(ent_name)

            self.log.warning(
                '-- entity "{}" is not synchronized to avalon. Skipping'.format(
                    ent_name
                )
            )
            return

        try:
            mongoid = ObjectId(mongoid)
        except Exception:
            error_key = 'Invalid MongoID on entities (try SyncToAvalon)'
            if error_key not in self.interface_messages:
                self.interface_messages[error_key] = []

            if ent_name not in self.interface_messages[error_key]:
                self.interface_messages[error_key].append(ent_name)

            self.log.warning(
                '-- entity "{}" has stored invalid MongoID. Skipping'.format(
                    ent_name
                )
            )
            return
        # Find entity in Mongo DB
        mongo_entity = self.db_con.find_one({'_id': mongoid})
        if not mongo_entity:
            error_key = 'Entities not found in Avalon DB (try SyncToAvalon)'
            if error_key not in self.interface_messages:
                self.interface_messages[error_key] = []

            if ent_name not in self.interface_messages[error_key]:
                self.interface_messages[error_key].append(ent_name)

            self.log.warning(
                '-- entity "{}" was not found in DB by id "{}". Skipping'.format(
                    ent_name, str(mongoid)
                )
            )
            return

        # Change value if entity has set it's own
        entity_value = custom_attributes[key]
        if entity_value is not None:
            value = entity_value

        data = mongo_entity.get('data') or {}

        data[key] = value
        self.db_con.update_many(
            {'_id': mongoid},
            {'$set': {'data': data}}
        )

        self.log.debug(
            '-- stored value "{}"'.format(value)
        )

        for child in entity.get('children', []):
            self.update_hierarchical_attribute(child, key, value)


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    SyncHierarchicalAttrs(session, plugins_presets).register()


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
