# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack
import sys
import argparse
import logging
import os
import ftrack_api
import json
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

        return True


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
            # TODO redo work!!!
            'template': {
                'work': '{root}/{project}/{hierarchy}/{asset}/work/{task}',
                'publish':'{root}/{project}/{hierarchy}/{asset}/publish/{family}/{subset}/v{version}/{projectcode}_{asset}_{subset}_v{version}.{representation}'}
        }

        # Set project template
        template = {"schema": "avalon-core:inventory-1.0"}

        # --- Create project and assets in Avalon ---
        io.install()
        ## ----- PROJECT ------
        # If project don't exists -> <Create project> ELSE <Update Config>
        if (io.find_one({'type': 'project',
                'name': entityProj['full_name']}) is None):
            inventory.save(entityProj['full_name'], config, template)
        else:
            io.update_many({'type': 'project','name': entityProj['full_name']},
                {'$set':{'config':config}})

        # Store info about project (FtrackId)
        io.update_many({'type': 'project','name': entityProj['full_name']},
            {'$set':{'data':{'code':entityProj['name'],'ftrackId':entityProj['id'],'entityType':entityProj.entity_type}}})

        # Store project Id
        projectId = io.find_one({"type": "project", "name": entityProj["full_name"]})["_id"]
        if custAttrName in entityProj['custom_attributes'] and entityProj['custom_attributes'][custAttrName] is '':
            entityProj['custom_attributes'][custAttrName] = str(projectId)

        # If entity is Project or have only 1 entity kill action
        if (len(eLinks) > 1) and not (eLinks[-1]['type'] in ['Project']):

            ## ----- ASSETS ------
            # Presets:
            # TODO how to check if entity is Asset Library or AssetBuild?
            silo = 'Assets' if eLinks[-1]['type'] in ['AssetBuild', 'Library'] else 'Film'
            os.environ['AVALON_SILO'] = silo
            # Get list of assets without project
            assets = []
            for i in range(1, len(eLinks)):
                assets.append(eLinks[i])

            folderStruct = []
            parentId = None
            data = {'visualParent': parentId, 'parents': folderStruct,
                    'tasks':None, 'ftrackId': None, 'entityType': None,
                    'hierarchy': ''}

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

                # Try to find asset in current database
                avalon_asset = io.find_one({'type': 'asset', 'name': asset['name']})
                # Create if don't exists
                if avalon_asset is None:
                    inventory.create_asset(asset['name'], silo, data, projectId)
                    print("Asset "+asset['name']+" - created")
                # Raise error if it seems to be different ent. with same name
                elif (avalon_asset['data']['ftrackId'] != data['ftrackId'] or
                    avalon_asset['data']['visualParent'] != data['visualParent'] or
                    avalon_asset['data']['parents'] != data['parents']):
                        raise ValueError('Possibility of entity name duplication: {}'.format(asset['name']))
                # Else update info
                else:
                    io.update_many({'type': 'asset','name': asset['name']},
                        {'$set':{'data':data, 'silo': silo}})
                    # TODO check if is asset in same folder!!! ???? FEATURE FOR FUTURE
                    print("Asset "+asset["name"]+" - updated")

                # Get parent ID and store it to data
                parentId = io.find_one({'type': 'asset', 'name': asset['name']})['_id']
                hierarchy = os.path.sep.join(folderStruct)
                data.update({'visualParent': parentId, 'parents': folderStruct,
                            'hierarchy': hierarchy})
                folderStruct.append(asset['name'])

            ## FTRACK FEATURE - FTRACK MUST HAVE avalon_mongo_id FOR EACH ENTITY TYPE EXCEPT TASK
            # Set custom attribute to avalon/mongo id of entity (parentID is last)
            if custAttrName in entity['custom_attributes'] and entity['custom_attributes'][custAttrName] is '':
                entity['custom_attributes'][custAttrName] = str(parentId)

        io.uninstall()

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
            print("action <" + self.__class__.__name__ + "> is running")

            #TODO AVALON_PROJECTS, AVALON_ASSET, AVALON_SILO should be set up otherwise console log shows avalon debug
            importable = []

            def getShotAsset(entity):
                if not (entity.entity_type in ['Task']):
                    if entity not in importable:
                        importable.append(entity)

                    if entity['children']:
                        childrens = entity['children']
                        for child in childrens:
                            getShotAsset(child)

            # get all entities separately/unique
            for entity in entities:
                getShotAsset(entity)

            for e in importable:
                self.importToAvalon(session, e)

            job['status'] = 'done'
            session.commit()
            print('Synchronization to Avalon was successfull!')

        except Exception as e:
            job['status'] = 'failed'
            print('During synchronization to Avalon went something wrong!')
            print(e)
            message = str(e)

        if len(message) > 0:
            return {
                'success': False,
                'message': message
            }

        return {
            'success': True,
            'message': "Synchronization was successfull"
        }


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
