# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack
import sys
import argparse
import logging
import os
import ftrack_api
import json
import re
from ftrack_action_handler import BaseAction

from avalon import io, inventory, lib
from avalon.vendor import toml

class SyncToAvalon(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'sync.to.avalon'
    #: Action label.
    label = 'SyncToAvalon'
    #: Action description.
    description = 'Send data from Ftrack to Avalon'
    #: Action icon.
    icon = 'https://cdn1.iconfinder.com/data/icons/hawcons/32/699650-icon-92-inbox-download-512.png'


    def discover(self, session, entities, event):
        ''' Validation '''
        discover = False
        for entity in entities:
            if entity.entity_type.lower() not in ['task', 'assetversion']:
                discover = True
                break

        return discover


    def launch(self, session, entities, event):
        message = ""

        # JOB SETTINGS
        userId = event['source']['user']['id']
        user = session.query('User where id is ' + userId).one()

        job = session.create('Job', {
            'user': user,
            'status': 'running',
            'data': json.dumps({
                'description': 'Synch Ftrack to Avalon.'
            })
        })

        try:
            self.log.info("action <" + self.__class__.__name__ + "> is running")

            #TODO AVALON_PROJECTS, AVALON_ASSET, AVALON_SILO should be set up otherwise console log shows avalon debug
            self.setAvalonAttributes(session)
            self.importable = []

            # get from top entity in hierarchy all parent entities
            top_entity = entities[0]['link']
            if len(top_entity) > 1:
                for e in top_entity:
                    parent_entity = session.get(e['type'], e['id'])
                    self.importable.append(parent_entity)

            # get all child entities separately/unique
            for entity in entities:
                self.getShotAsset(entity)

            # Check duplicate name - raise error if found
            all_names = {}
            duplicates = []

            for e in self.importable:
                name = self.checkName(e['name'])
                if name in all_names:
                    duplicates.append("'{}'-'{}'".format(all_names[name], e['name']))
                else:
                    all_names[name] = e['name']

            if len(duplicates) > 0:
                raise ValueError("Unable to sync: Entity name duplication: {}".format(", ".join(duplicates)))

            # Import all entities to Avalon DB
            for e in self.importable:
                self.importToAvalon(session, e)

            job['status'] = 'done'
            session.commit()
            self.log.info('Synchronization to Avalon was successfull!')

        except Exception as e:
            job['status'] = 'failed'
            message = str(e)
            self.log.error('During synchronization to Avalon went something wrong! ({})'.format(message))

        if len(message) > 0:
            return {
                'success': False,
                'message': message
            }

        return {
            'success': True,
            'message': "Synchronization was successfull"
        }
    def setAvalonAttributes(self, session):
        self.custom_attributes = []
        all_avalon_attr = session.query('CustomAttributeGroup where name is "avalon"').one()
        for cust_attr in all_avalon_attr['custom_attribute_configurations']:
            if 'avalon_' not in cust_attr['key']:
                self.custom_attributes.append(cust_attr)

    def getShotAsset(self, entity):
        if not (entity.entity_type in ['Task']):
            if entity not in self.importable:
                self.importable.append(entity)

            if entity['children']:
                childrens = entity['children']
                for child in childrens:
                    self.getShotAsset(child)

    def checkName(self, input_name):
        if input_name.find(" ") == -1:
            name = input_name
        else:
            name = input_name.replace(" ", "-")
            self.log.info("Name of {} was changed to {}".format(input_name, name))
        return name

    def getConfig(self, entity):
        apps = []
        for app in entity['custom_attributes']['applications']:
            try:
                label = toml.load(lib.which_app(app))['label']
                apps.append({'name':app, 'label':label})
            except Exception as e:
                self.log.error('Error with application {0} - {1}'.format(app, e))

        config = {
            'schema': 'avalon-core:config-1.0',
            'tasks': [{'name': ''}],
            'apps': apps,
            # TODO redo work!!!
            'template': {
                'workfile': '{asset[name]}_{task[name]}_v{version:0>3}<_{comment}>',
                'work': '{root}/{project}/{hierarchy}/{asset}/work/{task}',
                'publish':'{root}/{project}/{hierarchy}/{asset}/publish/{family}/{subset}/v{version}/{projectcode}_{asset}_{subset}_v{version}.{representation}'}
        }
        return config


    def importToAvalon(self, session, entity):
        eLinks = []

        ca_mongoid = 'avalon_mongo_id'

        # get needed info of entity and all parents
        for e in entity['link']:
            tmp = session.get(e['type'], e['id'])
            eLinks.append(tmp)

        entityProj = eLinks[0]

        # set AVALON_PROJECT env
        os.environ["AVALON_PROJECT"] = entityProj["full_name"]
        os.environ["AVALON_ASSET"] = entityProj['full_name']

        # Set project template
        template = {"schema": "avalon-core:inventory-1.0"}

        # --- Begin: PUSH TO Avalon ---
        io.install()
        ## ----- PROJECT ------
        # If project don't exists -> <Create project> ELSE <Update Config>
        avalon_project = io.find_one({"type": "project", "name": entityProj["full_name"]})
        entity_type = entity.entity_type

        data = {}
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
                ent_obj_type_id = session.query('ObjectType where name is "{}"'.format(entity_type)).one()['id']

                if cust_attr['object_type_id'] == ent_obj_type_id:
                    data[cust_attr['key']] = entity['custom_attributes'][cust_attr['key']]


        if entity.entity_type.lower() in ['project']:
            # Set project Config
            config = self.getConfig(entity)

            if avalon_project is None:
                inventory.save(entityProj['full_name'], config, template)
            else:
                io.update_many({'type': 'project','name': entityProj['full_name']},
                    {'$set':{'config':config}})

            data['code'] = entity['name']

            # Store info about project (FtrackId)
            io.update_many({
                'type': 'project',
                'name': entity['full_name']},
                {'$set':{'data':data}})

            projectId = io.find_one({"type": "project", "name": entityProj["full_name"]})["_id"]
            if ca_mongoid in entity['custom_attributes']:
                entity['custom_attributes'][ca_mongoid] = str(projectId)
            else:
                self.log.error("Custom attribute for <{}> is not created.".format(entity['name']))
            io.uninstall()
            return

        # Store project Id
        projectId = avalon_project["_id"]

        ## ----- ASSETS ------
        # Presets:
        # TODO how to check if entity is Asset Library or AssetBuild?
        if entity.entity_type in ['AssetBuild', 'Library']:
            silo = 'Assets'
        else:
            silo = 'Film'

        os.environ['AVALON_SILO'] = silo

        # Get list of parents without project
        parents = []
        for i in range(1, len(eLinks)-1):
            parents.append(eLinks[i])

        # Get info for 'Data' in Avalon DB
        tasks = []
        for child in entity['children']:
            if child.entity_type in ['Task']:
                tasks.append(child['name'])

        folderStruct = []
        parentId = None

        for parent in parents:
            name = self.checkName(parent['name'])
            folderStruct.append(name)
            parentId = io.find_one({'type': 'asset', 'name': name})['_id']
            if parent['parent'].entity_type != 'project' and parentId is None:
                self.importToAvalon(parent)
                parentId = io.find_one({'type': 'asset', 'name': name})['_id']

        hierarchy = os.path.sep.join(folderStruct)

        data['visualParent'] = parentId
        data['parents'] = folderStruct
        data['tasks'] = tasks
        data['hierarchy'] = hierarchy


        name = self.checkName(entity['name'])
        os.environ['AVALON_ASSET'] = name

        # Try to find asset in current database
        avalon_asset = io.find_one({'type': 'asset', 'name': name})
        # Create if don't exists
        if avalon_asset is None:
            inventory.create_asset(name, silo, data, projectId)
            self.log.debug("Asset {} - created".format(name))
        # Raise error if it seems to be different ent. with same name

        elif (avalon_asset['data']['ftrackId'] != data['ftrackId'] or
            avalon_asset['data']['visualParent'] != data['visualParent'] or
            avalon_asset['data']['parents'] != data['parents']):
                raise ValueError('Entity <{}> is not same'.format(name))
        # Else update info
        else:
            io.update_many({'type': 'asset','name': name},
                {'$set':{'data':data, 'silo': silo}})
            # TODO check if is asset in same folder!!! ???? FEATURE FOR FUTURE
            self.log.debug("Asset {} - updated".format(name))

        ## FTRACK FEATURE - FTRACK MUST HAVE avalon_mongo_id FOR EACH ENTITY TYPE EXCEPT TASK
        # Set custom attribute to avalon/mongo id of entity (parentID is last)
        if ca_mongoid in entity['custom_attributes']:
            entity['custom_attributes'][ca_mongoid] = str(parentId)
        else:
            self.log.error("Custom attribute for <{}> is not created.".format(entity['name']))

        io.uninstall()
        session.commit()


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = SyncToAvalon(session)
    action_handler.register()


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
