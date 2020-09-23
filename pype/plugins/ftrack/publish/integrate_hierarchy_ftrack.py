import sys
import six
import pyblish.api
from avalon import io
from pprint import pformat

try:
    from pype.modules.ftrack.lib.avalon_sync import CUST_ATTR_AUTO_SYNC
except Exception:
    CUST_ATTR_AUTO_SYNC = "avalon_auto_sync"


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
    families = ["shot"]
    optional = False

    def process(self, context):
        # additional inner methods
        def _get_assets(input_dict):
            """ Returns only asset dictionary.
                Usually the last part of deep dictionary which
                is not having any children
            """
            for key in input_dict.keys():
                # check if child key is available
                if input_dict[key].get("childs"):
                    # loop deeper
                    return _get_assets(input_dict[key]["childs"])
                else:
                    # give the dictionary with assets
                    return input_dict

        def _set_assets(input_dict, new_assets=None):
            """ Modify the hierarchy context dictionary.
                It will replace the asset dictionary with only the filtred one.
            """
            for key in input_dict.keys():
                # check if child key is available
                if input_dict[key].get("childs"):
                    # return if this is just for testing purpose and no
                    # new_assets property is avalable
                    if not new_assets:
                        return True

                    # test for deeper inner children availabelity
                    if _set_assets(input_dict[key]["childs"]):
                        # if one level deeper is still children available
                        # then process farther
                        _set_assets(input_dict[key]["childs"], new_assets)
                    else:
                        # or just assign the filtred asset ditionary
                        input_dict[key]["childs"] = new_assets
                else:
                    # test didnt find more childs in input dictionary
                    return None

        # processing starts here
        active_assets = []
        self.context = context
        if "hierarchyContext" not in self.context.data:
            return

        hierarchy_context = self.context.data["hierarchyContext"]
        hierarchy_assets = _get_assets(hierarchy_context)

        # filter only the active publishing insatnces
        for instance in self.context:
            if instance.data.get("publish") is False:
                continue

            if not instance.data.get("asset"):
                continue

            active_assets.append(instance.data["asset"])

        # filter out only assets which are activated as isntances
        new_hierarchy_assets = {k: v for k, v in hierarchy_assets.items()
                                if k in active_assets}

        # modify the hierarchy context so there are only fitred assets
        _set_assets(hierarchy_context, new_hierarchy_assets)

        self.log.debug(
            f"__ hierarchy_context: `{pformat(hierarchy_context)}`")

        self.session = self.context.data["ftrackSession"]
        project_name = self.context.data["projectEntity"]["name"]
        query = 'Project where full_name is "{}"'.format(project_name)
        project = self.session.query(query).one()
        auto_sync_state = project[
            "custom_attributes"][CUST_ATTR_AUTO_SYNC]

        if not io.Session:
            io.install()

        self.ft_project = None

        input_data = hierarchy_context

        # disable termporarily ftrack project's autosyncing
        if auto_sync_state:
            self.auto_sync_off(project)

        try:
            # import ftrack hierarchy
            self.import_to_ftrack(input_data)
        except Exception:
            raise
        finally:
            if auto_sync_state:
                self.auto_sync_on(project)

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

    def auto_sync_off(self, project):
        project["custom_attributes"][CUST_ATTR_AUTO_SYNC] = False

        self.log.info("Ftrack autosync swithed off")

        try:
            self.session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            self.session.rollback()
            raise

    def auto_sync_on(self, project):

        project["custom_attributes"][CUST_ATTR_AUTO_SYNC] = True

        self.log.info("Ftrack autosync swithed on")

        try:
            self.session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            self.session.rollback()
            raise
