import pyblish.api
from bson.objectid import ObjectId
from pype.ftrack import get_project_config
from avalon import schema
from avalon.tools.libraryloader.io_nonsingleton import DbConnector


class IntegrateInstancesToAvalon(pyblish.api.InstancePlugin):
    """
    Create entities in ftrack based on collected data from premiere

    """

    order = pyblish.api.IntegratorOrder + 0.48
    label = 'Integrate To Avalon'
    families = []

    exclude = []

    def process(self, instance):
        for ex in self.exclude:
            if ex in instance.data['families']:
                return

        self.log.debug('instance {}'.format(instance))

        self.db = DbConnector()
        # TODO implement how to get right data
        all_instances_data = {}
        self.import_to_ftrack(all_instances_data)

    def import_to_avalon(self, input_data, parent=None):
        for name in input_data:
            entity_data = input_data[name]
            entity_type = entity_data['entity_type']

            # # Data
            data = {}
            # CUSTOM ATTRIBUTES
            custom_attributes = entity_data.get('custom_attributes', [])
            for key in custom_attributes:
                data[key] = custom_attributes[key]

            # TASKS
            data['entityType'] = entity_type

            if entity_type.lower() == 'project':
                self.db.activate_project(name)
                entity = self.db.find_one({'type': 'project'})
                if entity is None:
                    # TODO better exception
                    raise Exception
                self.av_project = entity

            elif self.av_project is None or parent is None:
                # TODO better exception
                raise Exception
            else:
                tasks = entity_data.get('tasks', [])
                data['tasks'] = tasks
                data['visualParent'] = parent['_id']
                try:
                    entity = self.db.find_one({'type': 'asset', 'name': name})
                except Exception:
                    entity = None

            # Create entity if not exists
            if entity is None:
                entity = self.create_avalon_entity(name, entity_data)

            if entity_type.lower() == 'project':
                self.db.update_many(
                    {'_id': self.av_project['_id']},
                    {'$set': {
                        'data': data
                    }})
            else:
                self.db.update_many(
                    {'_id': entity['_id']},
                    {'$set': {
                        'data': data,
                        'parent': ObjectId(self.av_project['_id'])
                    }})

            if 'childs' in entity_data:
                self.import_to_ftrack(entity_data['childs'], entity)

    def create_avalon_entity(self, name, data):
        pass
