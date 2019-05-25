import pyblish.api
from avalon import io


class IntegrateHierarchyToAvalon(pyblish.api.ContextPlugin):
    """
    Create entities in ftrack based on collected data from premiere

    """

    order = pyblish.api.IntegratorOrder - 0.1
    label = 'Integrate Hierarchy To Avalon'
    families = ['clip']

    def process(self, context):
        if "hierarchyContext" not in context.data:
            return

        self.db = io
        if not self.db.Session:
            self.db.install()

        input_data = context.data["hierarchyContext"]
        self.import_to_avalon(input_data)

    def import_to_avalon(self, input_data, parent=None):

        for name in input_data:
            self.log.info('input_data[name]: {}'.format(input_data[name]))
            entity_data = input_data[name]
            entity_type = entity_data['entity_type']

            data = {}
            # Process project
            if entity_type.lower() == 'project':
                entity = self.db.find_one({'type': 'project'})
                # TODO: should be in validator?
                assert (entity is not None), "Didn't find project in DB"

                # get data from already existing project
                for key, value in entity.get('data', {}).items():
                    data[key] = value

                self.av_project = entity
            # Raise error if project or parent are not set
            elif self.av_project is None or parent is None:
                raise AssertionError(
                    "Collected items are not in right order!"
                )
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
                    self.log.info('entity: {}'.format(entity))
                    self.log.info('data: {}'.format(entity.get('data', {})))
                    self.log.info('____1____')
                    data['entityType'] = entity_type
                    # TASKS
                    tasks = entity_data.get('tasks', [])
                    if tasks is not None or len(tasks) > 0:
                        data['tasks'] = tasks
                    parents = []
                    visualParent = None
                    data = input_data[name]
                    if self.av_project['_id'] != parent['_id']:
                        visualParent = parent['_id']
                        parents.extend(parent.get('data', {}).get('parents', []))
                        parents.append(parent['name'])
                    data['visualParent'] = visualParent
                    data['parents'] = parents

                    self.db.update_many(
                        {'_id': entity['_id']},
                        {'$set': {
                            'data': data,
                        }})

                    entity = self.db.find_one({'type': 'asset', 'name': name})
                    self.log.info('entity: {}'.format(entity))
                    self.log.info('data: {}'.format(entity.get('data', {})))
                    self.log.info('____2____')

                # Else get data from already existing
                else:
                    self.log.info('entity: {}'.format(entity))
                    self.log.info('data: {}'.format(entity.get('data', {})))
                    self.log.info('________')
                    for key, value in entity.get('data', {}).items():
                        data[key] = value

                data['entityType'] = entity_type
                # TASKS
                tasks = entity_data.get('tasks', [])
                if tasks is not None or len(tasks) > 0:
                    data['tasks'] = tasks
                parents = []
                visualParent = None
                # do not store project's id as visualParent (silo asset)

                if self.av_project['_id'] != parent['_id']:
                    visualParent = parent['_id']
                    parents.extend(parent.get('data', {}).get('parents', []))
                    parents.append(parent['name'])
                data['visualParent'] = visualParent
                data['parents'] = parents

            # CUSTOM ATTRIBUTES
            for k, val in entity_data.get('custom_attributes', {}).items():
                data[k] = val

            # Update entity data with input data
            self.db.update_many(
                {'_id': entity['_id']},
                {'$set': {
                    'data': data,
                }})

            if 'childs' in entity_data:
                self.import_to_avalon(entity_data['childs'], entity)

    def create_avalon_asset(self, name, silo):
        item = {
            'schema': 'avalon-core:asset-2.0',
            'name': name,
            'silo': silo,
            'parent': self.av_project['_id'],
            'type': 'asset',
            'data': {}
        }
        entity_id = self.db.insert_one(item).inserted_id

        return self.db.find_one({'_id': entity_id})
