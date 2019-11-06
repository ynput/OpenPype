import os
import sys

from pype.ftrack.lib.io_nonsingleton import DbConnector

from pype.vendor import ftrack_api
from pype.ftrack import BaseEvent, lib
from bson.objectid import ObjectId


class SyncHierarchicalAttrs(BaseEvent):
    # After sync to avalon event!
    priority = 101
    db_con = DbConnector()
    ca_mongoid = lib.get_ca_mongoid()

    def launch(self, session, event):
        # Filter entities and changed values if it makes sence to run script
        processable = []
        processable_ent = {}
        for ent in event['data']['entities']:
            # Ignore entities that are not tasks or projects
            if ent['entityType'].lower() not in ['task', 'show']:
                continue

            action = ent.get("action")
            # skip if remove (Entity does not exist in Ftrack)
            if action == "remove":
                continue

            # When entity was add we don't care about keys
            if action != "add":
                keys = ent.get('keys')
                if not keys:
                    continue

            entity = session.get(self._get_entity_type(ent), ent['entityId'])
            processable.append(ent)

            processable_ent[ent['entityId']] = {
                "entity": entity,
                "action": action,
                "link": entity["link"]
            }

        if not processable:
            return True

        # Find project of entities
        ft_project = None
        for entity_dict in processable_ent.values():
            try:
                base_proj = entity_dict['link'][0]
            except Exception:
                continue
            ft_project = session.get(base_proj['type'], base_proj['id'])
            break

        # check if project is set to auto-sync
        if (
            ft_project is None or
            'avalon_auto_sync' not in ft_project['custom_attributes'] or
            ft_project['custom_attributes']['avalon_auto_sync'] is False
        ):
            return True

        # Get hierarchical custom attributes from "avalon" group
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

        self.db_con.install()
        self.db_con.Session['AVALON_PROJECT'] = ft_project['full_name']

        for ent in processable:
            entity_dict = processable_ent[ent['entityId']]

            entity = entity_dict["entity"]
            ent_path = "/".join([ent["name"] for ent in entity_dict['link']])
            action = entity_dict["action"]

            keys_to_process = {}
            if action == "add":
                # Store all custom attributes when entity was added
                for key in custom_attributes:
                    keys_to_process[key] = entity['custom_attributes'][key]
            else:
                # Update only updated keys
                for key in ent['keys']:
                    if key in custom_attributes:
                        keys_to_process[key] = entity['custom_attributes'][key]

            processed_keys = self.get_hierarchical_values(
                keys_to_process, entity
            )
            # Do the processing of values
            self.update_hierarchical_attribute(entity, processed_keys, ent_path)

        self.db_con.uninstall()

        return True

    def get_hierarchical_values(self, keys_dict, entity):
        # check already set values
        _set_keys = []
        for key, value in keys_dict.items():
            if value is not None:
                _set_keys.append(key)

        # pop set values from keys_dict
        set_keys = {}
        for key in _set_keys:
            set_keys[key] = keys_dict.pop(key)

        # find if entity has set values and pop them out
        keys_to_pop = []
        for key in keys_dict.keys():
            _val = entity["custom_attributes"][key]
            if _val:
                keys_to_pop.append(key)
                set_keys[key] = _val

        for key in keys_to_pop:
            keys_dict.pop(key)

        # if there are not keys to find value return found
        if not keys_dict:
            return set_keys

        # end recursion if entity is project
        if entity.entity_type.lower() == "project":
            for key, value in keys_dict.items():
                set_keys[key] = value

        else:
            result = self.get_hierarchical_values(keys_dict, entity["parent"])
            for key, value in result.items():
                set_keys[key] = value

        return set_keys

    def update_hierarchical_attribute(self, entity, keys_dict, ent_path):
        # TODO store all keys at once for entity
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

        changed_keys = {}
        data = mongo_entity.get('data') or {}
        for key, value in keys_dict.items():
            cur_value = data.get(key)
            if cur_value:
                if cur_value == value:
                    continue
            changed_keys[key] = value
            data[key] = value

        if not changed_keys:
            return

        self.log.debug(
            "{} - updated hierarchical attributes: {}".format(
                ent_path, str(changed_keys)
            )
        )

        self.db_con.update_many(
            {'_id': mongoid},
            {'$set': {'data': data}}
        )

        for child in entity.get('children', []):
            _keys_dict = {}
            for key, value in keys_dict.items():
                if key not in child.get('custom_attributes', {}):
                    continue
                child_value = child['custom_attributes'][key]
                if child_value is not None:
                    continue
                _keys_dict[key] = value

            if not _keys_dict:
                continue
            child_path = "/".join([ent["name"] for ent in child['link']])
            self.update_hierarchical_attribute(child, _keys_dict, child_path)


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''

    SyncHierarchicalAttrs(session, plugins_presets).register()
