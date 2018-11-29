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
        for ent in event['data']['entities']:
            if self.ca_mongoid in ent['keys']:
                return False
        self.proj = None

        for entity in entities:
            try:
                base_proj = entity['link'][0]
            except:
                continue
            self.proj = session.get(base_proj['type'], base_proj['id'])
            break

        if self.proj is None:
            return False

        os.environ["AVALON_PROJECT"] = self.proj['full_name']

        self.projectId = self.proj['custom_attributes'][self.ca_mongoid]

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
                message = "Please run 'Create Attributes' action or create custom attribute 'avalon_mongo_id' manually for {}".format(entity.entity_type)
                self.show_message(event, message, False)
                return

            if entity not in importEntities:
                importEntities.append(entity)

        if len(importEntities) < 1:
            return

        self.setAvalonAttributes()

        io.install()

        for entity in importEntities:
            self.importToAvalon(entity)

        io.uninstall()

        session.commit()

        if message != "":
            self.show_message(event, message, False)

        return True

    def importToAvalon(self, entity):
        data = {}

        entity_type = entity.entity_type

        type = 'asset'
        name = entity['name']
        silo = 'Film'
        if entity_type in ['Project']:
            type = 'project'
            name = entity['full_name']
            data['code'] = entity['name']
        elif entity_type in ['AssetBuild', 'Library']:
            silo = 'Assets'

        os.environ["AVALON_ASSET"] = name
        os.environ["AVALON_SILO"] = silo

        data['ftrackId'] = entity['id']
        data['entityType'] = entity_type

        for cust_attr in self.custom_attributes:
            key = cust_attr['key']
            if cust_attr['entity_type'].lower() in ['asset']:
                data[key] = entity['custom_attributes'][key]

            elif cust_attr['entity_type'].lower() in ['show'] and entity_type.lower() == 'project':
                data[key] = entity['custom_attributes'][key]

            elif cust_attr['entity_type'].lower() in ['task'] and entity_type.lower() != 'project':
                # Put space between capitals (e.g. 'AssetBuild' -> 'Asset Build')
                entity_type_full = re.sub(r"(\w)([A-Z])", r"\1 \2", entity_type)
                # Get object id of entity type
                ent_obj_type_id = self.session.query('ObjectType where name is "{}"'.format(entity_type_full)).one()['id']

                if cust_attr['object_type_id'] == ent_obj_type_id:
                    data[key] = entity['custom_attributes'][key]

        mongo_id = entity['custom_attributes'][self.ca_mongoid]

        if entity_type in ['Project']:
            config = ftrack_utils.get_config(entity)
            template = lib.get_avalon_project_template_schema()

            if self.avalon_project is None:
                inventory.save(name, config, template)
                self.avalon_project = io.find_one({'type': 'project', 'name': name})

            self.projectId = self.avalon_project['_id']
            data['code'] = entity['name']

            io.update_many(
                {"_id": ObjectId(self.projectId)},
                {'$set':{
                    'name':name,
                    'config':config,
                    'data':data,
                    }})
            try:
                entity['custom_attributes'][self.ca_mongoid] = str(self.projectId)
            except Exception as e:
                self.log.error(e)
            return


        if self.avalon_project is None:
            self.importToAvalon(self.proj)

        tasks = []
        for child in entity['children']:
            if child.entity_type in ['Task']:
                tasks.append(child['name'])

        folderStruct = []
        parentId = None

        parents = []
        for i in range(1, len(entity['link'])-1):
            tmp_type = entity['link'][i]['type']
            tmp_id = entity['link'][i]['id']
            tmp = self.session.get(tmp_type, tmp_id)
            parents.append(tmp)

        for parent in parents:
            parname = self.checkName(parent['name'])
            folderStruct.append(parname)
            avalonAarent = io.find_one({'type': 'asset', 'name': parname})
            if parent['parent'].entity_type != 'project' and avalonAarent is None:
                self.importToAvalon(parent)
            parentId = io.find_one({'type': 'asset', 'name': parname})['_id']

        hierarchy = os.path.sep.join(folderStruct)

        data['tasks'] = tasks
        if parentId is not None:
            data['parents'] = folderStruct
            data['visualParent'] = parentId
            data['hierarchy'] = hierarchy

        avalon_asset = None

        if mongo_id is not "":
            avalon_asset = io.find_one({'_id': ObjectId(mongo_id)})

        if avalon_asset is None:
            avalon_asset = io.find_one({'type': 'asset', 'name': name})
            if avalon_asset is None:
                mongo_id = inventory.create_asset(name, silo, data, ObjectId(self.projectId))
        else:
            if name != avalon_asset['name']:
                string = "'{}->{}'".format(name, avalon_asset['name'])
                if entity_type in ['Shot','AssetBuild']:
                    self.nameShotAsset.append(string)
                    mongo_id = inventory.create_asset(name, silo, data, ObjectId(self.projectId))
                else:
                    self.nameChanged.append(string)
                return

        io.update_many(
            {"_id": ObjectId(mongo_id)},
            {'$set':{
                'name':name,
                'silo':silo,
                'data':data,
                'parent': self.projectId}})

        try:
            entity['custom_attributes'][self.ca_mongoid] = str(mongo_id)
        except Exception as e:
            self.log.error(e)


    def checkName(self, input_name):
        if input_name.find(" ") == -1:
            name = input_name
        else:
            name = input_name.replace(" ", "-")
            print("Name of {} was changed to {}".format(input_name, name))
        return name

    def setAvalonAttributes(self):
        self.custom_attributes = []
        all_avalon_attr = self.session.query('CustomAttributeGroup where name is "avalon"').one()
        for cust_attr in all_avalon_attr['custom_attribute_configurations']:
            if 'avalon_' not in cust_attr['key']:
                self.custom_attributes.append(cust_attr)

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
