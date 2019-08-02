import os
import sys
import json
import argparse
import logging
import collections

from pypeapp import config
from pype.vendor import ftrack_api
from pype.ftrack import BaseAction, lib
from avalon.tools.libraryloader.io_nonsingleton import DbConnector
from bson.objectid import ObjectId


class SyncHierarchicalAttrs(BaseAction):

    db_con = DbConnector()
    ca_mongoid = lib.get_ca_mongoid()

    #: Action identifier.
    identifier = 'sync.hierarchical.attrs'
    #: Action label.
    label = 'Sync HierAttrs'
    #: Action description.
    description = 'Synchronize hierarchical attributes'
    #: Icon
    icon = '{}/ftrack/action_icons/SyncHierarchicalAttrs.svg'.format(
        os.environ.get(
            'PYPE_STATICS_SERVER',
            'http://localhost:{}'.format(
                config.get_presets().get('services', {}).get(
                    'statics_server', {}
                ).get('default_port', 8021)
            )
        )
    )

    def register(self):
        self.session.event_hub.subscribe(
            'topic=ftrack.action.discover',
            self._discover
        )

        self.session.event_hub.subscribe(
            'topic=ftrack.action.launch and data.actionIdentifier={}'.format(
                self.identifier
            ),
            self._launch
        )

    def discover(self, session, entities, event):
        ''' Validation '''
        role_check = False
        discover = False
        role_list = ['Pypeclub', 'Administrator', 'Project Manager']
        user = session.query(
            'User where id is "{}"'.format(event['source']['user']['id'])
        ).one()

        for role in user['user_security_roles']:
            if role['security_role']['name'] in role_list:
                role_check = True
                break

        if role_check is True:
            for entity in entities:
                context_type = entity.get('context_type', '').lower()
                if (
                    context_type in ('show', 'task') and
                    entity.entity_type.lower() != 'task'
                ):
                    discover = True
                    break

        return discover

    def launch(self, session, entities, event):
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

        process_session = ftrack_api.Session(
            server_url=session.server_url,
            api_key=session.api_key,
            api_user=session.api_user,
            auto_connect_event_hub=True
        )
        try:
            # Collect hierarchical attrs
            custom_attributes = {}
            all_avalon_attr = process_session.query(
                'CustomAttributeGroup where name is "avalon"'
            ).one()
            for cust_attr in all_avalon_attr['custom_attribute_configurations']:
                if 'avalon_' in cust_attr['key']:
                    continue

                if not cust_attr['is_hierarchical']:
                    continue

                if cust_attr['default']:
                    self.log.warning((
                        'Custom attribute "{}" has set default value.'
                        ' This attribute can\'t be synchronized'
                    ).format(cust_attr['label']))
                    continue

                custom_attributes[cust_attr['key']] = cust_attr

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
                for key in custom_attributes:
                    # check if entity has that attribute
                    if key not in entity['custom_attributes']:
                        self.log.debug(
                            'Hierachical attribute "{}" not found on "{}"'.format(
                                key, entity.get('name', entity)
                            )
                        )
                        continue

                    value = self.get_hierarchical_value(key, entity)
                    if value is None:
                        self.log.warning(
                            'Hierarchical attribute "{}" not set on "{}"'.format(
                                key, entity.get('name', entity)
                            )
                        )
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
        # collect entity's custom attributes
        custom_attributes = entity.get('custom_attributes')
        if not custom_attributes:
            return

        mongoid = custom_attributes.get(self.ca_mongoid)
        if not mongoid:
            self.log.debug('Entity "{}" is not synchronized to avalon.'.format(
                entity.get('name', entity)
            ))
            return

        try:
            mongoid = ObjectId(mongoid)
        except Exception:
            self.log.warning('Entity "{}" has stored invalid MongoID.'.format(
                entity.get('name', entity)
            ))
            return
        # Find entity in Mongo DB
        mongo_entity = self.db_con.find_one({'_id': mongoid})
        if not mongo_entity:
            self.log.warning(
                'Entity "{}" is not synchronized to avalon.'.format(
                    entity.get('name', entity)
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

        for child in entity.get('children', []):
            self.update_hierarchical_attribute(child, key, value)


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    SyncHierarchicalAttrs(session).register()


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
