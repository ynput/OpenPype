# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack
import sys
import argparse
import logging
import collections
import os

import json
import ftrack_api
from ftrack_action_handler.action import BaseAction

from avalon import io, inventory, schema
from avalon.vendor import toml


class SyncToAvalon(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'sync.to.avalon'

    #: Action label.
    label = 'SyncToAvalon'

    #: Action description.
    description = 'Send data from Ftrack to Avalon'

    def validate_selection(self, session, entities):
        '''Return if *entities* is a valid selection.'''
        # if (len(entities) != 1):
        #     # If entities contains more than one item return early since
        #     # metadata cannot be edited for several entites at the same time.
        #     return False
        pass
        # entity_type, entity_id = entities[0]
        # if (
        #     entity_type not in session.types
        # ):
        #     # Return False if the target entity does not have a metadata
        #     # attribute.
        #     return False

        return True

    def discover(self, session, entities, event):
        '''Return True if action is valid.'''

        self.logger.info('Got selection: {0}'.format(entities))
        return self.validate_selection(session, entities)

    def importToAvalon(self, session, entity):
        eLinks = []
        # TODO read from file, which data are in scope???
        """ get needed info of entity and all parents """
        for e in entity['link']:
            tmp = session.get(e['type'], e['id'])
            if e['name'].find(" ") == -1:
                name = e['name']
            else:
                name = e['name'].replace(" ", "-")
                print("Name of "+tmp.entity_type+" was changed from "+e['name']+" to "+name)

            eLinks.append({"type": tmp.entity_type, "name": name, "ftrackId": tmp['id']})

        entityProj = session.get(eLinks[0]['type'], eLinks[0]['ftrackId'])

        """ set AVALON_PROJECT env """
        os.environ["AVALON_PROJECT"] = entityProj["full_name"]

        # get schema of project TODO read different schemas based on project type
        template = {"schema": "avalon-core:inventory-1.0"}
        schema = entityProj['project_schema']['name']
        fname = os.path.join(os.path.dirname(
            os.path.realpath(__file__)),
            (schema + '.toml'))
        try:
            with open(fname) as f:
                config = toml.load(f)
        except IOError:
            raise

        # Create project in Avalon
        io.install()
        # Check if project exists -> Create project
        if (io.find_one(
                {"type": "project", "name": entityProj["full_name"]}) is None):
            inventory.save(entityProj["full_name"], config, template)

        # Store project Id
        projectId = io.find_one({"type": "project", "name": entityProj["full_name"]})["_id"]

        # If entity is Project or is Silo kill action
        if (len(eLinks) > 2) and not (eLinks[-1]['type'] in ['Project']):
            silo = eLinks[1]

            # Create Assets
            assets = []
            for i in range(2, len(eLinks)):
                assets.append(eLinks[i])

            folderStruct = []
            folderStruct.append(silo['name'])
            parentId = None
            data = {'ftrackId': None, 'visualParent': parentId, 'parents': folderStruct,
                    'entityType': None}

            for asset in assets:
                data = {'ftrackId': asset['ftrackId'], 'visualParent': data['visualParent'],
                        'parents': data['parents'], 'entityType': asset['type']}
                if (io.find_one({'type': 'asset', 'name': asset['name']}) == None):
                    inventory.create_asset(asset['name'], silo['name'], data, projectId)
                    print("Asset "+asset['name']+" created")

                else:
                    # TODO check if is asset in same folder!!! ???? FEATURE FOR FUTURE
                    # tmp = io.find_one({'type': 'asset', 'name': asset['name']})
                    print("Asset "+asset["name"]+" already exist")

                parentId = io.find_one({'type': 'asset', 'name': asset['name']})['_id']
                data = {'visualParent': parentId, 'parents': folderStruct, }
                folderStruct.append(asset['name'])

        io.uninstall()

    def launch(self, session, entities, event):
        """ JOB SETTING """
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
            importable = []

            def getShotAsset(entity):
                if not (entity.entity_type in ['Task']):
                    if not (entity in importable):
                        importable.append(entity)

                    if entity['children']:
                        childrens = entity['children']
                        for child in childrens:
                            getShotAsset(child)

            """ Get all Shots and AssetBuild from entities """
            for entity in entities:
                entity_type, entity_id = entity
                act_ent = session.get(entity_type, entity_id)
                getShotAsset(act_ent)

            # _handle_result -> by to mel resit
            # """ TODO Check if name of entities match REGEX"""
            # for entity in importable:
            #     for e in entity['link']:
            #         item = {
            #             "silo": "silo",
            #             "parent": "parent",
            #             "type": "asset",
            #             "schema": "avalon-core:asset-2.0",
            #             "name": e['name'],
            #             "data": dict(),
            #         }
            #         try:
            #             schema.validate(item)
            #         except Exception as e:
            #             print(e)
            # print(e['name'])
            # ftrack.EVENT_HUB.publishReply(
            #     event,
            #     data={
            #         'success': False,
            #         'message': 'Entity name contains invalid character!'
            #     }
            # )

            for e in importable:
                self.importToAvalon(session, e)

            job['status'] = 'done'
            session.commit()
        except:
            job['status'] = 'failed'
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

    session = ftrack_api.Session(
        server_url="https://pype.ftrackapp.com",
        api_key="4e01eda0-24b3-4451-8e01-70edc03286be",
        api_user="jakub.trllo"
    )
    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
