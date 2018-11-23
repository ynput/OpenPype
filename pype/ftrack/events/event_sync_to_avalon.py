import os
import sys
import ftrack_api
from ftrack_event_handler import BaseEvent
from avalon import io, inventory, lib
from avalon.vendor import toml
import re
from bson.objectid import ObjectId

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
        exceptions = ['assetversion', 'job', 'user']

        for entity in entities:
            if entity.entity_type.lower() in exceptions:
                continue
            elif entity.entity_type.lower() in ['task']:
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

        type = 'asset'
        name = entity['name']
        silo = 'Film'
        if entity.entity_type == 'Project':
            type = 'project'
            name = entity['full_name']
            data['code'] = entity['name']
        elif entity.entity_type in ['AssetBuild', 'Library']:
            silo = 'Assets'

        os.environ["AVALON_ASSET"] = name
        os.environ["AVALON_SILO"] = silo

        entity_type = entity.entity_type

        data['ftrackId'] = entity['id']
        data['entityType'] = entity_type

        for cust_attr in self.custom_attributes:
            if cust_attr['entity_type'].lower() in ['asset']:
                data[cust_attr['key']] = entity['custom_attributes'][cust_attr['key']]

            elif cust_attr['entity_type'].lower() in ['show'] and entity_type.lower() == 'project':
                data[cust_attr['key']] = entity['custom_attributes'][cust_attr['key']]

            elif cust_attr['entity_type'].lower() in ['task'] and entity_type.lower() != 'project':
                # Put space between capitals (e.g. 'AssetBuild' -> 'Asset Build')
                entity_type = re.sub(r"(\w)([A-Z])", r"\1 \2", entity_type)
                # Get object id of entity type
                ent_obj_type_id = self.session.query('ObjectType where name is "{}"'.format(entity_type)).one()['id']

                if cust_attr['object_type_id'] == ent_obj_type_id:
                    data[cust_attr['key']] = entity['custom_attributes'][cust_attr['key']]

        mongo_id = entity['custom_attributes'][self.ca_mongoid]


        if entity_type in ['project']:
            config = self.getConfig()
            template = {"schema": "avalon-core:inventory-1.0"}

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

        if self.avalon_project is None:
            self.importToAvalon(self.proj)

        avalon_asset = io.find_one({'_id': ObjectId(mongo_id)})
        if avalon_asset is None:
            avalon_asset = io.find_one({'type': type, 'name': name})
        if avalon_asset is None:
            mongo_id = inventory.create_asset(name, silo, data, self.projectId)

        io.update_many(
            {"_id": ObjectId(mongo_id)},
            {'$set':{
                'name':name,
                'silo':silo,
                'data':data,
                'Parent': self.projectId}})


    def checkName(self, input_name):
        if input_name.find(" ") == -1:
            name = input_name
        else:
            name = input_name.replace(" ", "-")
            print("Name of {} was changed to {}".format(input_name, name))
        return name

    def getConfig(self, entity):
        apps = []
        for app in entity['custom_attributes']['applications']:
            try:
                label = toml.load(lib.which_app(app))['label']
                apps.append({'name':app, 'label':label})
            except Exception as e:
                print('Error with application {0} - {1}'.format(app, e))

        config = {
            'schema': 'avalon-core:config-1.0',
            'tasks': [{'name': ''}],
            'apps': apps,
            # TODO redo work!!!
            'template': {
                'workfile': '{asset[name]}_{task[name]}_{version:0>3}<_{comment}>',
                'work': '{root}/{project}/{hierarchy}/{asset}/work/{task}',
                'publish':'{root}/{project}/{hierarchy}/{asset}/publish/{family}/{subset}/v{version}/{projectcode}_{asset}_{subset}_v{version}.{representation}'}
        }
        return config

    def setAvalonAttributes(self):
        self.custom_attributes = []
        all_avalon_attr = self.session.query('CustomAttributeGroup where name is "avalon"').one()
        for cust_attr in all_avalon_attr['custom_attribute_configurations']:
            if 'avalon_' not in cust_attr['key']:
                self.custom_attributes.append(cust_attr)

def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    event = Sync_to_Avalon(session)
    event.register()
