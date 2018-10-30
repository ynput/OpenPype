# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack
import sys
import argparse
import logging
import os
import json
import ftrack_api
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

    def validate_selection(self, session, entities):
        '''Return if *entities* is a valid selection.'''
        # if (len(entities) != 1):
        #     # If entities contains more than one item return early since
        #     # metadata cannot be edited for several entites at the same time.
        #     return False
        # entity_type, entity_id = entities[0]
        # if (
        #     entity_type not in session.types
        # ):
        #     # Return False if the target entity does not have a metadata
        #     # attribute.
        #     return False
        pass
        return True

    def discover(self, session, entities, event):
        '''Return True if action is valid.'''

        self.logger.info('Got selection: {0}'.format(entities))
        return self.validate_selection(session, entities)


    def importToAvalon(self, session, entity):
        eLinks = []
        custAttrName = 'avalon_mongo_id'
        # TODO read from file, which data are in scope???
        # get needed info of entity and all parents
        for e in entity['link']:
            tmp = session.get(e['type'], e['id'])
            if e['name'].find(" ") == -1:
                name = e['name']
            else:
                name = e['name'].replace(" ", "-")
                print("Name of "+tmp.entity_type+" - "+e['name']+" was changed to "+name)

            eLinks.append({"type": tmp.entity_type, "name": name, "ftrackId": tmp['id']})

        entityProj = session.get(eLinks[0]['type'], eLinks[0]['ftrackId'])

        # set AVALON_PROJECT env
        os.environ["AVALON_PROJECT"] = entityProj["full_name"]
        os.environ["AVALON_ASSET"] = entityProj['full_name']

        # Get apps from Ftrack / TODO Exceptions?!!!
        apps = []
        for app in entityProj['custom_attributes']['applications']:
            try:
                label = toml.load(lib.which_app(app))['label']
                apps.append({'name':app, 'label':label})
            except Exception as e:
                print('Error with application {0} - {1}'.format(app, e))

        # Set project Config
        config = {
            'schema': 'avalon-core:config-1.0',
            'tasks': [{'name': ''}],
            'apps': apps,
            'template': {'work': '','publish':''}
        }

        # Set project template
        template = {"schema": "avalon-core:inventory-1.0"}

        # --- Create project and assets in Avalon ---
        io.install()
        # If project don't exists -> <Create project> ELSE <Update Config>
        if (io.find_one({'type': 'project',
                'name': entityProj['full_name']}) is None):
            inventory.save(entityProj['full_name'], config, template)
        else:
            io.update_many({'type': 'project','name': entityProj['full_name']},
                {'$set':{'config':config}})

        # Store info about project (FtrackId)
        io.update_many({'type': 'project','name': entityProj['full_name']},
            {'$set':{'data':{'ftrackId':entityProj['id'],'entityType':entityProj.entity_type}}})

        # Store project Id
        projectId = io.find_one({"type": "project", "name": entityProj["full_name"]})["_id"]
        if custAttrName in entityProj['custom_attributes'] and entityProj['custom_attributes'][custAttrName] is '':
            entityProj['custom_attributes'][custAttrName] = str(projectId)

        # If entity is Project or have only 1 entity kill action
        if (len(eLinks) > 1) and not (eLinks[-1]['type'] in ['Project']):

            # TODO how to check if entity is Asset Library or AssetBuild?
            silo = 'Assets' if eLinks[-1]['type'] in ['AssetBuild', 'Library'] else 'Film'
            os.environ['AVALON_SILO'] = silo
            # Create Assets
            assets = []
            for i in range(1, len(eLinks)):
                assets.append(eLinks[i])

            folderStruct = []
            parentId = None
            data = {'visualParent': parentId, 'parents': folderStruct,
                    'tasks':None, 'ftrackId': None, 'entityType': None}

            for asset in assets:
                os.environ['AVALON_ASSET'] = asset['name']
                data.update({'ftrackId': asset['ftrackId'], 'entityType': asset['type']})
                # Get tasks of each asset
                assetEnt = session.get('TypedContext', asset['ftrackId'])
                tasks = []
                for child in assetEnt['children']:
                    if child.entity_type in ['Task']:
                        tasks.append(child['name'])
                data.update({'tasks': tasks})

                if (io.find_one({'type': 'asset', 'name': asset['name']}) is None):
                    # Create asset in DB
                    inventory.create_asset(asset['name'], silo, data, projectId)
                    print("Asset "+asset['name']+" - created")
                else:
                    io.update_many({'type': 'asset','name': asset['name']},
                        {'$set':{'data':data}})
                    # TODO check if is asset in same folder!!! ???? FEATURE FOR FUTURE
                    print("Asset "+asset["name"]+" - already exist")

                parentId = io.find_one({'type': 'asset', 'name': asset['name']})['_id']
                data.update({'visualParent': parentId, 'parents': folderStruct})
                folderStruct.append(asset['name'])


            # Set custom attribute to avalon/mongo id of entity (parentID is last)
            if custAttrName in entity['custom_attributes'] and entity['custom_attributes'][custAttrName] is '':
                entity['custom_attributes'][custAttrName] = str(parentId)

        io.uninstall()

    def launch(self, session, entities, event):
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
            print("action <" + self.__class__.__name__ + "> is running")
            #TODO It's better to have these env set, are they used anywhere?
            os.environ['AVALON_PROJECTS'] = "tmp"
            os.environ['AVALON_ASSET'] = "tmp"
            os.environ['AVALON_SILO'] = "tmp"
            importable = []

            def getShotAsset(entity):
                if not (entity.entity_type in ['Task']):
                    if entity not in importable:
                        importable.append(entity)

                    if entity['children']:
                        childrens = entity['children']
                        for child in childrens:
                            getShotAsset(child)

            # get all entities separately
            for entity in entities:
                entity_type, entity_id = entity
                act_ent = session.get(entity_type, entity_id)
                getShotAsset(act_ent)

            for e in importable:
                self.importToAvalon(session, e)

            job['status'] = 'done'
            session.commit()

            print('Synchronization to Avalon was successfull!')
        except Exception as e:
            job['status'] = 'failed'
            print('During synchronization to Avalon went something wrong!')
            print(e)

        return True


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = SyncToAvalon(session)
    action_handler.register()
    print("----- action - <" + action_handler.__class__.__name__ + "> - Has been registered -----")


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
