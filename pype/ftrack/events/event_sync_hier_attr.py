import os
import sys

from pype.ftrack.lib.custom_db_connector import DbConnector

from pype.vendor import ftrack_api
from pype.ftrack import BaseEvent, lib
from bson.objectid import ObjectId


class SyncHierarchicalAttrs(BaseEvent):
    # After sync to avalon event!
    priority = 101
    db_con = lib.custom_db_connector.DbConnector(
        mongo_url=os.environ["AVALON_MONGO"],
        database_name=os.environ["AVALON_DB"],
        table_name=None
    )
    def launch(self, session, event):
        self.project_name = None
        # Filter entities and changed values if it makes sence to run script
        processable = []
        for ent in event['data']['entities']:
            keys = ent.get('keys')
            if not keys:
                continue
            processable.append(ent)

        if not processable:
            return True

        custom_attributes = {}
        query = 'CustomAttributeGroup where name is "avalon"'
        all_avalon_attr = session.query(query).one()
        for cust_attr in all_avalon_attr['custom_attribute_configurations']:
            if 'avalon_' in cust_attr['key']:
                continue
            if not cust_attr['is_hierarchical']:
                continue
            custom_attributes[cust_attr['key']] = cust_attr

        if not custom_attributes:
            return True

        for ent in processable:
            for key in ent['keys']:
                if key not in custom_attributes:
                    continue

                entity_query = '{} where id is "{}"'.format(
                    ent['entity_type'], ent['entityId']
                )
                entity = self.session.query(entity_query).one()
                attr_value = entity['custom_attributes'][key]
                if not self.project_name:
                    # TODO this is not 100% sure way
                    if entity.entity_type.lower() == 'project':
                        self.project_name = entity['full_name']
                    else:
                        self.project_name = entity['project']['full_name']
                    if not self.project_name:
                        continue
                    self.db_con.active_table = self.project_name
                    self.db_con.install()
                # TODO rewrite?
                # ------DRY is not here :/-------
                ca_mongoid = lib.get_ca_mongoid()
                custom_attributes = entity.get('custom_attributes')
                if not custom_attributes:
                    continue

                mongoid = custom_attributes.get(ca_mongoid)
                if not mongoid:
                    continue

                try:
                    mongoid = ObjectId(mongoid)
                except Exception:
                    continue

                mongo_entity = self.db_con.find_one({'_id': mongoid})
                if not mongo_entity:
                    continue

                data = mongo_entity.get('data') or {}
                cur_value = data.get(key)
                if cur_value:
                    if cur_value == attr_value:
                        continue

                data[key] = attr_value
                self.db_con.update_one(
                    {'_id': mongoid},
                    {'$set': {'data': data}}
                )
                # -------------
                self.update_hierarchical_attribute(entity, key, attr_value)

        self.db_con.uninstall()

        return True

    def update_hierarchical_attribute(self, entity, key, value):
        ca_mongoid = lib.get_ca_mongoid()

        for child in entity.get('children', []):
            custom_attributes = child.get('custom_attributes')
            if not custom_attributes:
                continue

            child_value = custom_attributes.get(key)

            if child_value is not None:
                if child_value != value:
                    continue
            mongoid = custom_attributes.get(ca_mongoid)
            if not mongoid:
                continue

            try:
                mongoid = ObjectId(mongoid)
            except Exception:
                continue

            mongo_entity = self.db_con.find_one({'_id': mongoid})
            if not mongo_entity:
                continue

            data = mongo_entity.get('data') or {}
            cur_value = data.get(key)
            if cur_value:
                if cur_value == value:
                    continue

            data[key] = value
            self.db_con.update_one(
                {'_id': mongoid},
                {'$set': {'data': data}}
            )

            self.update_hierarchical_attribute(child, key, value)


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''
    if not isinstance(session, ftrack_api.session.Session):
        return

    SyncHierarchicalAttrs(session).register()
