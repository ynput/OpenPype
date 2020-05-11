import sys

import six
import pyblish.api
from avalon import io


class IntegrateHierarchyToFtrack(pyblish.api.ContextPlugin):
    """
    Create entities in ftrack based on collected data from premiere
    Example of entry data:
    {
        "ProjectXS": {
            "entity_type": "Project",
            "custom_attributes": {
                "fps": 24,...
            },
            "tasks": [
                "Compositing",
                "Lighting",... *task must exist as task type in project schema*
            ],
            "childs": {
                "sq01": {
                    "entity_type": "Sequence",
                    ...
                }
            }
        }
    }
    """

    order = pyblish.api.IntegratorOrder - 0.04
    label = 'Integrate Hierarchy To Ftrack'
    families = ["clip", "shot"]
    optional = False

    def process(self, context):
        self.context = context
        if "hierarchyContext" not in context.data:
            return

        if not io.Session:
            io.install()

        self.ft_project = None
        self.session = context.data["ftrackSession"]

        input_data = context.data["hierarchyContext"]

        self.import_to_ftrack(input_data)

    def import_to_ftrack(self, input_data, parent=None):
        for entity_name in input_data:
            entity_data = input_data[entity_name]
            entity_type = entity_data['entity_type']
            self.log.debug(entity_data)
            self.log.debug(entity_type)

            if entity_type.lower() == 'project':
                query = 'Project where full_name is "{}"'.format(entity_name)
                entity = self.session.query(query).one()
                self.ft_project = entity
                self.task_types = self.get_all_task_types(entity)

            elif self.ft_project is None or parent is None:
                raise AssertionError(
                    "Collected items are not in right order!"
                )

            # try to find if entity already exists
            else:
                query = (
                    'TypedContext where name is "{0}" and '
                    'project_id is "{1}"'
                ).format(entity_name, self.ft_project["id"])
                try:
                    entity = self.session.query(query).one()
                except Exception:
                    entity = None

            # Create entity if not exists
            if entity is None:
                entity = self.create_entity(
                    name=entity_name,
                    type=entity_type,
                    parent=parent
                )
            # self.log.info('entity: {}'.format(dict(entity)))
            # CUSTOM ATTRIBUTES
            custom_attributes = entity_data.get('custom_attributes', [])
            instances = [
                i for i in self.context if i.data['asset'] in entity['name']
            ]
            for key in custom_attributes:
                assert (key in entity['custom_attributes']), (
                    'Missing custom attribute key: `{0}` in attrs: '
                    '`{1}`'.format(key, entity['custom_attributes'].keys())
                )

                entity['custom_attributes'][key] = custom_attributes[key]

                for instance in instances:
                    instance.data['ftrackEntity'] = entity

                try:
                    self.session.commit()
                except Exception:
                    tp, value, tb = sys.exc_info()
                    self.session.rollback()
                    six.reraise(tp, value, tb)

            # TASKS
            tasks = entity_data.get('tasks', [])
            existing_tasks = []
            tasks_to_create = []
            for child in entity['children']:
                if child.entity_type.lower() == 'task':
                    existing_tasks.append(child['name'].lower())
                    # existing_tasks.append(child['type']['name'])

            for task in tasks:
                if task.lower() in existing_tasks:
                    print("Task {} already exists".format(task))
                    continue
                tasks_to_create.append(task)

            for task in tasks_to_create:
                self.create_task(
                    name=task,
                    task_type=task,
                    parent=entity
                )
                try:
                    self.session.commit()
                except Exception:
                    tp, value, tb = sys.exc_info()
                    self.session.rollback()
                    six.reraise(tp, value, tb)

            # Incoming links.
            self.create_links(entity_data, entity)
            try:
                self.session.commit()
            except Exception:
                tp, value, tb = sys.exc_info()
                self.session.rollback()
                six.reraise(tp, value, tb)

            if 'childs' in entity_data:
                self.import_to_ftrack(
                    entity_data['childs'], entity)

    def create_links(self, entity_data, entity):
        # Clear existing links.
        for link in entity.get("incoming_links", []):
            self.session.delete(link)
            try:
                self.session.commit()
            except Exception:
                tp, value, tb = sys.exc_info()
                self.session.rollback()
                six.reraise(tp, value, tb)

        # Create new links.
        for input in entity_data.get("inputs", []):
            input_id = io.find_one({"_id": input})["data"]["ftrackId"]
            assetbuild = self.session.get("AssetBuild", input_id)
            self.log.debug(
                "Creating link from {0} to {1}".format(
                    assetbuild["name"], entity["name"]
                )
            )
            self.session.create(
                "TypedContextLink", {"from": assetbuild, "to": entity}
            )

    def get_all_task_types(self, project):
        tasks = {}
        proj_template = project['project_schema']
        temp_task_types = proj_template['_task_type_schema']['types']

        for type in temp_task_types:
            if type['name'] not in tasks:
                tasks[type['name']] = type

        return tasks

    def create_task(self, name, task_type, parent):
        task = self.session.create('Task', {
            'name': name,
            'parent': parent
        })
        # TODO not secured!!! - check if task_type exists
        self.log.info(task_type)
        self.log.info(self.task_types)
        task['type'] = self.task_types[task_type]

        try:
            self.session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            self.session.rollback()
            six.reraise(tp, value, tb)

        return task

    def create_entity(self, name, type, parent):
        entity = self.session.create(type, {
            'name': name,
            'parent': parent
        })
        try:
            self.session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            self.session.rollback()
            six.reraise(tp, value, tb)

        return entity
