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


class ExpectedError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


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
        self.errors = []
        # get project
        for entity in entities:
            try:
                base_proj = entity['link'][0]
            except:
                continue
            self.proj = session.get(base_proj['type'], base_proj['id'])
            break

        # check if project is set to auto-sync
        if (
            self.proj is None or
            'avalon_auto_sync' not in self.proj['custom_attributes'] or
            self.proj['custom_attributes']['avalon_auto_sync'] is False
        ):
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
            self.avalon_project = io.find_one({
                "_id": ObjectId(self.projectId)
            })
        except:
            self.avalon_project = None

        importEntities = []
        if self.avalon_project is None:
            self.avalon_project = io.find_one({
                "type": "project",
                "name": self.proj["full_name"]
            })
            if self.avalon_project is None:
                importEntities.append(self.proj)
            else:
                self.projectId = self.avalon_project['_id']

        io.uninstall()

        for entity in entities:
            if entity.entity_type.lower() in ['task']:
                entity = entity['parent']

            if (
                'custom_attributes' not in entity or
                self.ca_mongoid not in entity['custom_attributes']
            ):
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
                self.importToAvalon(session, event, entity)
                session.commit()

        except ExpectedError as ee:
            items = []
            for error in self.errors:
                info = {
                    'label': 'Error',
                    'type': 'textarea',
                    'name': 'error',
                    'value': error
                }
                items.append(info)
                self.log.warning(error)
            self.show_interface(event, items)

        except Exception as e:
            message = str(e)
            ftrack_message = "SyncToAvalon event ended with unexpected error please check log file for more information."
            items = [{
                'label': 'Error',
                'type': 'textarea',
                'name': 'error',
                'value': ftrack_message
            }]
            self.show_interface(event, items)
            self.log.error(message)

        io.uninstall()

        return

    def importToAvalon(self, session, event, entity):
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
                self.avalon_project = io.find_one({'type': type, 'name': name})

            elif self.avalon_project['name'] != name:
                entity['name'] = self.avalon_project['name']
                session.commit()

                msg = 'You can\'t change name {} to {}, avalon wouldn\'t work properly!\nName was changed back!'.format(self.avalon_project['name'], name)
                self.errors.append(msg)
                return

            self.projectId = self.avalon_project['_id']

            data = ftrack_utils.get_data(self, entity, session, self.custom_attributes)

            io.update_many(
                {"_id": ObjectId(self.projectId)},
                {'$set': {
                    'name': name,
                    'config': config,
                    'data': data,
                    }})

            entity['custom_attributes'][self.ca_mongoid] = str(self.projectId)

            return

        if self.avalon_project is None:
            self.importToAvalon(session, event, self.proj)

        data = ftrack_utils.get_data(self, entity, session, self.custom_attributes)

        # only check name if entity is silo
        if len(data['parents']) == 0:
            if self.checkSilo(entity, event, session) is False:
                raise ExpectedError
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
            elif (
                avalon_asset['data']['parents'] != data['parents'] or
                avalon_asset['silo'] != silo
            ):
                msg = 'In Avalon DB already exists entity with name "{0}"'.format(name)
                self.errors.append(msg)
                return
        else:
            if avalon_asset['name'] != entity['name']:
                if self.checkChilds(entity) is False:
                    msg = 'You can\'t change name {} to {}, avalon wouldn\'t work properly!\n\nName was changed back!\n\nCreate new entity if you want to change name.'.format(avalon_asset['name'], entity['name'])
                    entity['name'] = avalon_asset['name']
                    session.commit()
                    self.errors.append(msg)

            if avalon_asset['silo'] != silo or avalon_asset['data']['parents'] != data['parents']:
                old_path = "/".join(avalon_asset['data']['parents'])
                new_path = "/".join(data['parents'])
                msg = 'You can\'t move with entities.\nEntity "{}" was moved from "{}" to "{}"\n\nAvalon won\'t work properly, please move them back!'.format(avalon_asset['name'], old_path, new_path)
                self.errors.append(msg)

        if len(self.errors) > 0:
            raise ExpectedError

        io.update_many(
            {"_id": ObjectId(mongo_id)},
            {'$set': {
                'name': name,
                'silo': silo,
                'data': data,
                'parent': ObjectId(self.projectId)}})

        entity['custom_attributes'][self.ca_mongoid] = str(mongo_id)

    def checkChilds(self, entity):
        if (entity.entity_type.lower() != 'task' and 'children' not in entity):
            return True
        childs = entity['children']
        for child in childs:
            if child.entity_type.lower() == 'task':
                config = ftrack_utils.get_config_data()
                if 'sync_to_avalon' in config:
                    config = config['sync_to_avalon']
                if 'statuses_name_change' in config:
                    available_statuses = config['statuses_name_change']
                else:
                    available_statuses = []
                ent_status = child['status']['name'].lower()
                if ent_status not in available_statuses:
                    return False
            # If not task go deeper
            elif self.checkChilds(child) is False:
                return False
        # If everything is allright
        return True

    def checkSilo(self, entity, event, session):
        changes = event['data']['entities'][0]['changes']
        if 'name' not in changes:
            return True
        new_name = changes['name']['new']
        old_name = changes['name']['old']

        if 'children' not in entity or len(entity['children']) < 1:
            return True

        if self.checkChilds(entity) is True:
            self.updateSilo(old_name, new_name)
            return True

        new_found = 0
        old_found = 0
        for asset in io.find({'silo': new_name}):
            new_found += 1
        for asset in io.find({'silo': old_name}):
            old_found += 1

        if new_found > 0 or old_found == 0:
            return True

        # If any condition is possible, show error to user and change name back
        msg = 'You can\'t change name {} to {}, avalon wouldn\'t work properly!\n\nName was changed back!\n\nCreate new entity if you want to change name.'.format(old_name, new_name)
        self.errors.append(msg)
        entity['name'] = old_name
        session.commit()

        return False

    def updateSilo(self, old, new):
        io.update_many(
            {'silo': old},
            {'$set': {'silo': new}}
        )

    def setAvalonAttributes(self):
        self.custom_attributes = []
        query = 'CustomAttributeGroup where name is "avalon"'
        all_avalon_attr = self.session.query(query).one()
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
        exceptions = [
            'assetversion', 'job', 'user', 'reviewsessionobject', 'timer',
            'socialfeed', 'timelog'
        ]
        _selection = event['data'].get('entities', [])

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
