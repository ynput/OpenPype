import os
import sys
import argparse
import logging
import json
import collections
import time

from pypeapp import config
from pype.vendor import ftrack_api
from pype.ftrack import BaseAction, lib
from pype.vendor.ftrack_api import session as fa_session


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
    identifier = 'sync.to.avalon'
    #: Action label.
    label = "Pype Admin"
    variant = "- Sync To Avalon (Server)"
    #: Action description.
    description = 'Send data from Ftrack to Avalon'
    #: Action icon.
    icon = '{}/ftrack/action_icons/PypeAdmin.svg'.format(
        os.environ.get(
            'PYPE_STATICS_SERVER',
            'http://localhost:{}'.format(
                config.get_presets().get('services', {}).get(
                    'statics_server', {}
                ).get('default_port', 8021)
            )
        )
    )

    project_query = (
        "select full_name, name, custom_attributes"
        ", project_schema._task_type_schema.types.name"
        " from Project where full_name is \"{}\""
    )

    entities_query = (
        "select id, name, parent_id, link, custom_attributes"
        " from TypedContext where project.full_name is \"{}\""
    )

    # Entity type names(lowered) that won't be synchronized with their children
    ignore_entity_types = ["task", "milestone"]

    def register(self):
        self.session.event_hub.subscribe(
            'topic=ftrack.action.discover',
            self._discover
        )

        self.session.event_hub.subscribe(
            'topic=ftrack.action.launch and data.actionIdentifier={0}'.format(
                self.identifier
            ),
            self._launch
        )

    def discover(self, session, entities, event):
        ''' Validation '''
        roleCheck = False
        discover = False
        roleList = ['Pypeclub', 'Administrator', 'Project Manager']
        userId = event['source']['user']['id']
        user = session.query('User where id is ' + userId).one()

        for role in user['user_security_roles']:
            if role['security_role']['name'] in roleList:
                roleCheck = True
                break
        if roleCheck is True:
            for entity in entities:
                if entity.entity_type.lower() not in ['task', 'assetversion']:
                    discover = True
                    break

        return discover

    def launch(self, session, entities, event):
        time_start = time.time()
        message = ""

        # JOB SETTINGS
        userId = event['source']['user']['id']
        user = session.query('User where id is ' + userId).one()

        job = session.create('Job', {
            'user': user,
            'status': 'running',
            'data': json.dumps({
                'description': 'Sync Ftrack to Avalon.'
            })
        })
        session.commit()
        try:
            self.log.debug("Preparing entities for synchronization")

            if entities[0].entity_type.lower() == "project":
                ft_project_name = entities[0]["full_name"]
            else:
                ft_project_name = entities[0]["project"]["full_name"]

            project_entities = session.query(
                self.entities_query.format(ft_project_name)
            ).all()

            ft_project = session.query(
                self.project_query.format(ft_project_name)
            ).one()

            entities_by_id = {}
            entities_by_parent = collections.defaultdict(list)

            entities_by_id[ft_project["id"]] = ft_project
            for ent in project_entities:
                entities_by_id[ent["id"]] = ent
                entities_by_parent[ent["parent_id"]].append(ent)

            importable = []
            for ent_info in event["data"]["selection"]:
                ent = entities_by_id[ent_info["entityId"]]
                for link_ent_info in ent["link"]:
                    link_ent = entities_by_id[link_ent_info["id"]]
                    if (
                        ent.entity_type.lower() in self.ignore_entity_types or
                        link_ent in importable
                    ):
                        continue

                    importable.append(link_ent)

            def add_children(parent_id):
                ents = entities_by_parent[parent_id]
                for ent in ents:
                    if ent.entity_type.lower() in self.ignore_entity_types:
                        continue

                    if ent not in importable:
                        importable.append(ent)

                    add_children(ent["id"])

            # add children of selection to importable
            for ent_info in event["data"]["selection"]:
                add_children(ent_info["entityId"])

            # Check names: REGEX in schema/duplicates - raise error if found
            all_names = []
            duplicates = []

            for entity in importable:
                lib.avalon_check_name(entity)
                if entity.entity_type.lower() == "project":
                    continue

                if entity['name'] in all_names:
                    duplicates.append("'{}'".format(entity['name']))
                else:
                    all_names.append(entity['name'])

            if len(duplicates) > 0:
                # TODO Show information to user and return False
                raise ValueError(
                    "Entity name duplication: {}".format(", ".join(duplicates))
                )

            # ----- PROJECT ------
            avalon_project = lib.get_avalon_project(ft_project)
            custom_attributes = lib.get_avalon_attr(session)

            # Import all entities to Avalon DB
            for entity in importable:
                result = lib.import_to_avalon(
                    session=session,
                    entity=entity,
                    ft_project=ft_project,
                    av_project=avalon_project,
                    custom_attributes=custom_attributes
                )
                # TODO better error handling
                # maybe split into critical, warnings and messages?
                if 'errors' in result and len(result['errors']) > 0:
                    job['status'] = 'failed'
                    session.commit()

                    lib.show_errors(self, event, result['errors'])

                    return {
                        'success': False,
                        'message': "Sync to avalon FAILED"
                    }

                if avalon_project is None:
                    if 'project' in result:
                        avalon_project = result['project']

            job['status'] = 'done'
            session.commit()

        except ValueError as ve:
            # TODO remove this part!!!!
            job['status'] = 'failed'
            session.commit()
            message = str(ve)
            self.log.error(
                'Error during syncToAvalon: {}'.format(message),
                exc_info=True
            )

        except Exception as e:
            job['status'] = 'failed'
            session.commit()
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log_message = "{}/{}/Line: {}".format(
                exc_type, fname, exc_tb.tb_lineno
            )
            self.log.error(
                'Error during syncToAvalon: {}'.format(log_message),
                exc_info=True
            )
            # TODO add traceback to message and show to user
            message = (
                'Unexpected Error'
                ' - Please check Log for more information'
            )

        finally:
            if job['status'] in ['queued', 'running']:
                job['status'] = 'failed'

            session.commit()

            time_end = time.time()
            self.log.debug("Synchronization took \"{}\"".format(
                str(time_end - time_start)
            ))

            if job["status"] != "failed":
                self.log.debug("Triggering Sync hierarchical attributes")
                self.trigger_action("sync.hierarchical.attrs", event)

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


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    SyncToAvalon(session, plugins_presets).register()


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
