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
        self.proj = None

        for entity in entities:
            try:
                base_proj = entity['link'][0]
            except:
                continue
            self.proj = session.get(base_proj['type'], base_proj['id'])
            break

        if self.proj is None:
            return

        os.environ["AVALON_PROJECT"] = self.proj['full_name']

        proj_id = self.proj['custom_attributes'][self.ca_mongoid]

        io.install()
        self.avalon_project = io.find({"_id": ObjectId(proj_id)})
        self.projectId = proj_id
        if self.avalon_project is None:
            self.avalon_project = io.find_one({"type": "project", "name": self.proj["full_name"]})
            self.projectId = self.avalon_project['_id']
        io.uninstall()

        self.importEntities = []

        for entity in entities:
            if entity.entity_type.lower() in ['task']:
                entity = entity['parent']
            try:
                mongo_id = entity['custom_attributes'][self.ca_mongoid]
            except:
                return {
                    'success': False,
                    'message': "Please run 'Create Attributes' action or create custom attribute 'avalon_mongo_id' manually for {}".format(entity.entity_type)
                }

            if entity not in self.importEntities:
                self.importEntities.append(entity)

        if len(self.importEntities) < 1:
            return

        self.setAvalonAttributes()

        io.install()

        for entity in self.importEntities:
            self.importToAvalon(entity)

        io.uninstall()

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


        if entity_type.lower() in ['project']:

            config = ftrack_utils.get_config(entity)
            template = lib.get_avalon_project_template_schema()

            if self.avalon_project is None:
                mongo_id = inventory.save(self.proj['full_name'], config, template)

                self.avalon_project = io.find({"_id": ObjectId(mongo_id)})
                self.projectId = mongo_id
                if self.avalon_project is None:
                    self.avalon_project = io.find_one({"type": "project", "name": self.proj["full_name"]})
                    self.projectId = self.avalon_project['_id']

            io.update_many(
                {"_id": ObjectId(mongo_id)},
                {'$set':{
                    'name':name,
                    'config':config,
                    'data':data,
                    }})
            return


        if self.avalon_project is None:
            self.importToAvalon(self.proj)

        eLinks = []
        for e in entity['link']:
            tmp = self.session.get(e['type'], e['id'])
            eLinks.append(tmp)

        tasks = []
        for child in entity['children']:
            if child.entity_type in ['Task']:
                tasks.append(child['name'])

        folderStruct = []
        parents = []
        for i in range(1, len(eLinks)-1):
            parents.append(eLinks[i])

        for parent in parents:
            parname = self.checkName(parent['name'])
            folderStruct.append(parname)
            parentId = io.find_one({'type': 'asset', 'name': parname})['_id']
            if parent['parent'].entity_type != 'project' and parentId is None:
                self.importToAvalon(parent)
                parentId = io.find_one({'type': 'asset', 'name': parname})['_id']

        hierarchy = os.path.sep.join(folderStruct)

        data['tasks'] = tasks
        data['parents'] = folderStruct
        data['visualParent'] = parentId
        data['hierarchy'] = hierarchy

        avalon_asset = io.find_one({'_id': ObjectId(mongo_id)})
        if avalon_asset is None:
            avalon_asset = io.find_one({'type': type, 'name': name})
            if avalon_asset is None:
                mongo_id = inventory.create_asset(name, silo, data, self.projectId)
        elif avalon_asset['name'] != name:
            mongo_id = inventory.create_asset(name, silo, data, self.projectId)

        io.update_many(
            {"_id": ObjectId(mongo_id)},
            {'$set':{
                'name':name,
                'silo':silo,
                'data':data,
                'parent': self.projectId}})


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
