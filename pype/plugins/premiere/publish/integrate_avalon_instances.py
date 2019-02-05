import pyblish.api
from avalon import io


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

        self.db = io
        self.db.install()
        # TODO implement how to get right data
        all_instances_data = {}
        self.import_to_avalon(all_instances_data)

    def import_to_avalon(self, input_data, parent=None):
        for name in input_data:
            entity_data = input_data[name]
            entity_type = entity_data['entity_type']

            data = {}
            # Process project
            if entity_type.lower() == 'project':
                # TODO: this should be already set if io...?
                if self.db.Session['AVALON_PROJECT'] is None:
                    self.db.Session['AVALON_PROJECT'] = name

                entity = self.db.find_one({'type': 'project'})
                if entity is None:
                    # TODO: better exception
                    raise Exception

                # get data from already existing project
                for key, value in entity.get('data', {}).items():
                    data[key] = value

                self.av_project = entity
            # Raise error if project or parent are not set
            elif self.av_project is None or parent is None:
                # TODO better exception
                raise Exception
            # Else process assset
            else:
                entity = self.db.find_one({'type': 'asset', 'name': name})
                # Create entity if doesn't exist
                if entity is None:
                    if self.av_project['_id'] == parent['_id']:
                        silo = None
                    elif parent['silo'] is None:
                        silo = parent['name']
                    else:
                        silo = parent['silo']
                    entity = self.create_avalon_asset(name, silo)
                # Else get data from already existing
                else:
                    for key, value in entity.get('data', {}).items():
                        data[key] = value

                data['entityType'] = entity_type
                # TASKS
                tasks = entity_data.get('tasks', [])
                data['tasks'] = tasks
                parents = []
                visualParent = None
                # do not store project's id as visualParent (silo asset)
                if self.av_project['_id'] != parent['_id']:
                    visualParent = parent['_id']
                    parents.extend(parent['data']['parents'])
                    parents.append(parent['name'])
                data['visualParent'] = visualParent
                data['parents'] = parents

            # CUSTOM ATTRIBUTES
            for key, value in entity_data.get('custom_attributes', {}).items():
                data[key] = value

            # Update entity data with input data
            self.db.update_many(
                {'_id': entity['_id']},
                {'$set': {
                    'data': data,
                }})

            if 'childs' in entity_data:
                self.import_to_ftrack(entity_data['childs'], entity)

    def create_avalon_asset(self, name, silo):
        item = {
            'schema': 'avalon-core:asset-2.0',
            'name': name,
            'silo': silo,
            'parent': self.av_project['_id'],
            'type': 'asset'
        }
        entity_id = self.db.insert_one(item).inserted_id

        return self.db.find_one({'_id': entity_id})
