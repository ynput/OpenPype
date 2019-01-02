import sys
import argparse
import logging
import os
import ftrack_api
import json
import re
from pype import lib
from ftrack_action_handler import BaseAction
from bson.objectid import ObjectId
from avalon import io, inventory

from pype.ftrack import ftrack_utils

class SyncToAvalon(BaseAction):
    '''
    Synchronizing data action - from Ftrack to Avalon DB

    Stores all information about entity.
    - Name(string) - Most important information = identifier of entity
    - Parent(ObjectId) - Avalon Project Id, if entity is not project itself
    - Silo(string) - Last parent except project
    - Data(dictionary):
        - VisualParent(ObjectId) - Avalon Id of parent asset
        - Parents(array of string) - All parent names except project
        - Tasks(array of string) - Tasks on asset
        - FtrackId(string)
        - entityType(string) - entity's type on Ftrack
        * All Custom attributes in group 'Avalon' which name don't start with 'avalon_'

    * These information are stored also for all parents and children entities.

    Avalon ID of asset is stored to Ftrack -> Custom attribute 'avalon_mongo_id'.
    - action IS NOT creating this Custom attribute if doesn't exist
        - run 'Create Custom Attributes' action or do it manually (Not recommended)

    If Ftrack entity already has Custom Attribute 'avalon_mongo_id' that stores ID:
    - name, parents and silo are checked -> shows error if are not exact the same
        - after sync it is not allowed to change names or move entities

    If ID in 'avalon_mongo_id' is empty string or is not found in DB:
    - tries to find entity by name
        - found:
            - raise error if ftrackId/visual parent/parents are not same
        - not found:
            - Creates asset/project

    '''

    #: Action identifier.
    identifier = 'sync.to.avalon.local'
    #: Action label.
    label = 'SyncToAvalon - Local'
    #: Action description.
    description = 'Send data from Ftrack to Avalon'
    #: Action icon.
    icon = 'https://cdn1.iconfinder.com/data/icons/hawcons/32/699650-icon-92-inbox-download-512.png'


    def discover(self, session, entities, event):
        ''' Validation '''
        roleCheck = False
        discover = False
        roleList = ['Pypeclub']
        userId = event['source']['user']['id']
        user = session.query('User where id is ' + userId).one()

        for role in user['user_security_roles']:
            if role['security_role']['name'] in roleList:
                roleCheck = True
        if roleCheck is True:
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
            self.log.info("Action <" + self.__class__.__name__ + "> is running")
            self.ca_mongoid = 'avalon_mongo_id'
            #TODO AVALON_PROJECTS, AVALON_ASSET, AVALON_SILO should be set up otherwise console log shows avalon debug
            self.setAvalonAttributes()
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

            # Check names: REGEX in schema/duplicates - raise error if found
            all_names = []
            duplicates = []

            for e in self.importable:
                ftrack_utils.avalon_check_name(e)
                if e['name'] in all_names:
                    duplicates.append("'{}'".format(e['name']))
                else:
                    all_names.append(e['name'])

            if len(duplicates) > 0:
                raise ValueError("Entity name duplication: {}".format(", ".join(duplicates)))

            ## ----- PROJECT ------
            # store Ftrack project- self.importable[0] must be project entity!!!
            self.entityProj = self.importable[0]
            # set AVALON_ env
            os.environ["AVALON_PROJECT"] = self.entityProj["full_name"]
            os.environ["AVALON_ASSET"] = self.entityProj["full_name"]

            self.avalon_project = None

            io.install()

            # Import all entities to Avalon DB
            for e in self.importable:
                self.importToAvalon(session, e)

            io.uninstall()

            job['status'] = 'done'
            session.commit()
            self.log.info('Synchronization to Avalon was successfull!')

        except ValueError as ve:
            job['status'] = 'failed'
            session.commit()
            message = str(ve)
            self.log.error('Error during syncToAvalon: {}'.format(message))

        except Exception as e:
            job['status'] = 'failed'
            session.commit()
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log_message = "{}/{}/Line: {}".format(exc_type, fname, exc_tb.tb_lineno)
            self.log.error('Error during syncToAvalon: {}'.format(log_message))
            message = 'Unexpected Error - Please check Log for more information'

        if len(message) > 0:
            message = "Unable to sync: {}".format(message)
            return {
                'success': False,
                'message': message
            }

        return {
            'success': True,
            'message': "Synchronization was successfull"
        }

    def setAvalonAttributes(self):
        self.custom_attributes = []
        all_avalon_attr = self.session.query('CustomAttributeGroup where name is "avalon"').one()
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

    def importToAvalon(self, session, entity):
        # --- Begin: PUSH TO Avalon ---

        entity_type = entity.entity_type

        if entity_type.lower() in ['project']:
            # Set project Config
            config = ftrack_utils.get_config(entity)
            # Set project template
            template = lib.get_avalon_project_template_schema()
            if self.ca_mongoid in entity['custom_attributes']:
                try:
                    projectId = ObjectId(self.entityProj['custom_attributes'][self.ca_mongoid])
                    self.avalon_project = io.find_one({"_id": projectId})
                except:
                    self.log.debug("Entity {} don't have stored entity id in ftrack".format(entity['name']))

            if self.avalon_project is None:
                self.avalon_project = io.find_one({
                    "type": "project",
                    "name": entity["full_name"]
                })
                if self.avalon_project is None:
                    inventory.save(entity['full_name'], config, template)
                    self.avalon_project = io.find_one({
                        "type": "project",
                        "name": entity["full_name"]
                    })

            elif self.avalon_project['name'] != entity['full_name']:
                raise ValueError('You can\'t change name {} to {}, avalon DB won\'t work properly!'.format(self.avalon_project['name'], name))

            data = ftrack_utils.get_data(self, entity, session,self.custom_attributes)

            # Store info about project (FtrackId)
            io.update_many({
                'type': 'project',
                'name': entity['full_name']
                }, {
                '$set':{'data':data, 'config':config}
                })

            self.projectId = self.avalon_project["_id"]
            if self.ca_mongoid in entity['custom_attributes']:
                entity['custom_attributes'][self.ca_mongoid] = str(self.projectId)
            else:
                self.log.error('Custom attribute for "{}" is not created.'.format(entity['name']))
            return

        ## ----- ASSETS ------
        # Presets:
        data = ftrack_utils.get_data(self, entity, session, self.custom_attributes)

        # return if entity is silo
        if len(data['parents']) == 0:
            return
        else:
            silo = data['parents'][0]

        os.environ['AVALON_SILO'] = silo

        name = entity['name']
        os.environ['AVALON_ASSET'] = name


        # Try to find asset in current database
        avalon_asset = None
        if self.ca_mongoid in entity['custom_attributes']:
            try:
                entityId = ObjectId(entity['custom_attributes'][self.ca_mongoid])
                avalon_asset = io.find_one({"_id": entityId})
            except:
                self.log.debug("Entity {} don't have stored entity id in ftrack".format(entity['name']))

        if avalon_asset is None:
            avalon_asset = io.find_one({'type': 'asset', 'name': name})
            # Create if don't exists
            if avalon_asset is None:
                inventory.create_asset(name, silo, data, self.projectId)
                self.log.debug("Asset {} - created".format(name))

            # Raise error if it seems to be different ent. with same name
            elif (avalon_asset['data']['parents'] != data['parents'] or
                avalon_asset['silo'] != silo):
                    raise ValueError('In Avalon DB already exists entity with name "{0}"'.format(name))

        elif avalon_asset['name'] != entity['name']:
            raise ValueError('You can\'t change name {} to {}, avalon DB won\'t work properly - please set name back'.format(avalon_asset['name'], name))
        elif avalon_asset['silo'] != silo or avalon_asset['data']['parents'] != data['parents']:
            old_path = "/".join(avalon_asset['data']['parents'])
            new_path = "/".join(data['parents'])
            raise ValueError('You can\'t move with entities. Entity "{}" was moved from "{}" to "{}" '.format(avalon_asset['name'], old_path, new_path))

        # Update info
        io.update_many({'type': 'asset','name': name},
            {'$set':{'data':data, 'silo': silo}})

        self.log.debug("Asset {} - updated".format(name))

        entityId = io.find_one({'type': 'asset', 'name': name})['_id']
        ## FTRACK FEATURE - FTRACK MUST HAVE avalon_mongo_id FOR EACH ENTITY TYPE EXCEPT TASK
        # Set custom attribute to avalon/mongo id of entity (parentID is last)
        if self.ca_mongoid in entity['custom_attributes']:
            entity['custom_attributes'][self.ca_mongoid] = str(entityId)
        else:
            self.log.error("Custom attribute for <{}> is not created.".format(entity['name']))

        session.commit()


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = SyncToAvalon(session)
    action_handler.register(200)


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
