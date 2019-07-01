import os
import sys

from avalon.tools.libraryloader.io_nonsingleton import DbConnector

from pype.vendor import ftrack_api
from pype.ftrack import BaseEvent, lib
from bson.objectid import ObjectId


class SyncHierarchicalAttrs(BaseEvent):
    # After sync to avalon event!
    priority = 101
    db_con = DbConnector()
    ca_mongoid = lib.get_ca_mongoid()

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
                    self.db_con.install()
                    self.db_con.Session['AVALON_PROJECT'] = self.project_name

                self.update_hierarchical_attribute(entity, key, attr_value)

        self.db_con.uninstall()

        return True

    def update_hierarchical_attribute(self, entity, key, value):
        custom_attributes = entity.get('custom_attributes')
        if not custom_attributes:
            return

        mongoid = custom_attributes.get(self.ca_mongoid)
        if not mongoid:
            return

        try:
            mongoid = ObjectId(mongoid)
        except Exception:
            return

        mongo_entity = self.db_con.find_one({'_id': mongoid})
        if not mongo_entity:
            return

        data = mongo_entity.get('data') or {}
        cur_value = data.get(key)
        if cur_value:
            if cur_value == attr_value:
                return

        data[key] = attr_value
        self.db_con.update_one(
            {'_id': mongoid},
            {'$set': {'data': data}}
        )

        for child in entity.get('children', []):
            self.update_one_entity(child, key, value)


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''
    if not isinstance(session, ftrack_api.session.Session):
        return

    SyncHierarchicalAttrs(session).register()
