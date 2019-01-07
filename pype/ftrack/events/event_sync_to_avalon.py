import os
import sys
import re
import ftrack_api
from ftrack_event_handler import BaseEvent
from pype import lib
from avalon import io, inventory
from avalon.vendor import toml
from bson.objectid import ObjectId
from pype.ftrack import ftrack_utils

class Sync_to_Avalon(BaseEvent):

    def launch(self, session, entities, event):

        self.ca_mongoid = 'avalon_mongo_id'
        # If mongo_id textfield has changed: RETURN!
        # - infinite loop
        for ent in event['data']['entities']:
            if 'keys' in ent:
                if self.ca_mongoid in ent['keys']:
                    return
        self.proj = None

        # get project
        for entity in entities:
            try:
                base_proj = entity['link'][0]
            except:
                continue
            self.proj = session.get(base_proj['type'], base_proj['id'])
            break

        # check if project is set to auto-sync
        if (self.proj is None or
            'avalon_auto_sync' not in self.proj['custom_attributes'] or
            self.proj['custom_attributes']['avalon_auto_sync'] is False):
                return

        # check if project have Custom Attribute 'avalon_mongo_id'
        if self.ca_mongoid not in self.proj['custom_attributes']:
            message = "Custom attribute '{}' for 'Project' is not created or don't have set permissions for API".format(self.ca_mongoid)
            self.log.warning(message)
            self.show_message(event, message, False)
            return

        self.projectId = self.proj['custom_attributes'][self.ca_mongoid]

        os.environ["AVALON_PROJECT"] = self.proj['full_name']

        # get avalon project if possible
        io.install()
        try:
            self.avalon_project = io.find_one({"_id": ObjectId(self.projectId)})
        except:
            self.avalon_project = None

        importEntities = []
        if self.avalon_project is None:
            self.avalon_project = io.find_one({"type": "project", "name": self.proj["full_name"]})
            if self.avalon_project is None:
                importEntities.append(self.proj)
            else:
                self.projectId = self.avalon_project['_id']

        io.uninstall()

        for entity in entities:
            if entity.entity_type.lower() in ['task']:
                entity = entity['parent']

            try:
                mongo_id = entity['custom_attributes'][self.ca_mongoid]
            except:
                message = "Custom attribute '{}' for '{}' is not created or don't have set permissions for API".format(self.ca_mongoid, entity.entity_type)
                self.log.warning(message)
                self.show_message(event, message, False)
                return

            if entity not in importEntities:
                importEntities.append(entity)

        if len(importEntities) < 1:
            return

        self.setAvalonAttributes()

        io.install()
        try:
            for entity in importEntities:
                self.importToAvalon(session, entity)
                session.commit()

        except ValueError as ve:
            message = str(ve)
            self.show_message(event, message, False)
            self.log.warning(message)

        except Exception as e:
            message = str(e)
            ftrack_message = "SyncToAvalon event ended with unexpected error please check log file for more information."
            self.show_message(event, ftrack_message, False)
            self.log.error(message)

        io.uninstall()

        return

    def importToAvalon(self, session, entity):
        if self.ca_mongoid not in entity['custom_attributes']:
            raise ValueError("Custom attribute '{}' for '{}' is not created or don't have set permissions for API".format(self.ca_mongoid, entity['name']))

        ftrack_utils.avalon_check_name(entity)

        entity_type = entity.entity_type

        if entity_type in ['Project']:
            type = 'project'
            name = entity['full_name']
            config = ftrack_utils.get_config(entity)
            template = lib.get_avalon_project_template_schema()

            if self.avalon_project is None:
                inventory.save(name, config, template)
                self.avalon_project = io.find_one({'type': 'project', 'name': name})

            elif self.avalon_project['name'] != name:
                raise ValueError('You can\'t change name {} to {}, avalon DB won\'t work properly!'.format(self.avalon_project['name'], name))

            self.projectId = self.avalon_project['_id']

            data = ftrack_utils.get_data(self, entity, session,self.custom_attributes)

            io.update_many(
                {"_id": ObjectId(self.projectId)},
                {'$set':{
                    'name':name,
                    'config':config,
                    'data':data,
                    }})

            entity['custom_attributes'][self.ca_mongoid] = str(self.projectId)

            return

        if self.avalon_project is None:
            self.importToAvalon(session, self.proj)

        data = ftrack_utils.get_data(self, entity, session,self.custom_attributes)

        # return if entity is silo
        if len(data['parents']) == 0:
            return
        else:
            silo = data['parents'][0]

        name = entity['name']

        os.environ["AVALON_ASSET"] = name
        os.environ['AVALON_SILO'] = silo

        avalon_asset = None
        # existence of this custom attr is already checked
        mongo_id = entity['custom_attributes'][self.ca_mongoid]

        if mongo_id is not "":
            avalon_asset = io.find_one({'_id': ObjectId(mongo_id)})

        if avalon_asset is None:
            avalon_asset = io.find_one({'type': 'asset', 'name': name})
            if avalon_asset is None:
                mongo_id = inventory.create_asset(name, silo, data, ObjectId(self.projectId))
            # Raise error if it seems to be different ent. with same name
            elif (avalon_asset['data']['parents'] != data['parents'] or
                avalon_asset['silo'] != silo):
                    raise ValueError('In Avalon DB already exists entity with name "{0}"'.format(name))
        elif avalon_asset['name'] != entity['name']:
            raise ValueError('You can\'t change name {} to {}, avalon DB won\'t work properly - please set name back'.format(avalon_asset['name'], name))
        elif avalon_asset['silo'] != silo or avalon_asset['data']['parents'] != data['parents']:
            old_path = "/".join(avalon_asset['data']['parents'])
            new_path = "/".join(data['parents'])
            raise ValueError('You can\'t move with entities. Entity "{}" was moved from "{}" to "{}" , avalon DB won\'t work properly'.format(avalon_asset['name'], old_path, new_path))


        io.update_many(
            {"_id": ObjectId(mongo_id)},
            {'$set':{
                'name':name,
                'silo':silo,
                'data':data,
                'parent': ObjectId(self.projectId)}})

        entity['custom_attributes'][self.ca_mongoid] = str(mongo_id)

    def setAvalonAttributes(self):
        self.custom_attributes = []
        all_avalon_attr = self.session.query('CustomAttributeGroup where name is "avalon"').one()
        for cust_attr in all_avalon_attr['custom_attribute_configurations']:
            if 'avalon_' not in cust_attr['key']:
                self.custom_attributes.append(cust_attr)

    def _launch(self, event):
        self.session.reset()

        args = self._translate_event(
            self.session, event
        )

        self.launch(
            self.session, *args
        )
        return
        
    def _translate_event(self, session, event):
        exceptions = ['assetversion', 'job', 'user', 'reviewsessionobject', 'timer', 'socialfeed', 'timelog']
        _selection = event['data'].get('entities',[])

        _entities = list()
        for entity in _selection:
            if entity['entityType'] in exceptions:
                continue
            _entities.append(
                (
                    session.get(self._get_entity_type(entity), entity.get('entityId'))
                )
            )

        return [_entities, event]

def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    event = Sync_to_Avalon(session)
    event.register()
