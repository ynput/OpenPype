import sys
import collections
import six
import pyblish.api
from copy import deepcopy
from openpype.pipeline import legacy_io

# Copy of constant `openpype_modules.ftrack.lib.avalon_sync.CUST_ATTR_AUTO_SYNC`
CUST_ATTR_AUTO_SYNC = "avalon_auto_sync"
CUST_ATTR_GROUP = "openpype"


# Copy of `get_pype_attr` from openpype_modules.ftrack.lib
# TODO import from openpype's ftrack module when possible to not break Python 2
def get_pype_attr(session, split_hierarchical=True):
    custom_attributes = []
    hier_custom_attributes = []
    # TODO remove deprecated "avalon" group from query
    cust_attrs_query = (
        "select id, entity_type, object_type_id, is_hierarchical, default"
        " from CustomAttributeConfiguration"
        # Kept `pype` for Backwards Compatiblity
        " where group.name in (\"pype\", \"{}\")"
    ).format(CUST_ATTR_GROUP)
    all_avalon_attr = session.query(cust_attrs_query).all()
    for cust_attr in all_avalon_attr:
        if split_hierarchical and cust_attr["is_hierarchical"]:
            hier_custom_attributes.append(cust_attr)
            continue

        custom_attributes.append(cust_attr)

    if split_hierarchical:
        # return tuple
        return custom_attributes, hier_custom_attributes

    return custom_attributes


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
    hosts = ["hiero", "resolve", "standalonepublisher", "flame"]
    optional = False

    def process(self, context):
        self.context = context
        if "hierarchyContext" not in self.context.data:
            return

        hierarchy_context = self._get_active_assets(context)
        self.log.debug("__ hierarchy_context: {}".format(hierarchy_context))

        self.session = self.context.data["ftrackSession"]
        project_name = self.context.data["projectEntity"]["name"]
        query = 'Project where full_name is "{}"'.format(project_name)
        project = self.session.query(query).one()
        auto_sync_state = project[
            "custom_attributes"][CUST_ATTR_AUTO_SYNC]

        if not legacy_io.Session:
            legacy_io.install()

        self.ft_project = None

        # disable termporarily ftrack project's autosyncing
        if auto_sync_state:
            self.auto_sync_off(project)

        try:
            # import ftrack hierarchy
            self.import_to_ftrack(hierarchy_context)
        except Exception:
            raise
        finally:
            if auto_sync_state:
                self.auto_sync_on(project)

    def import_to_ftrack(self, input_data, parent=None):
        # Prequery hiearchical custom attributes
        hier_custom_attributes = get_pype_attr(self.session)[1]
        hier_attr_by_key = {
            attr["key"]: attr
            for attr in hier_custom_attributes
        }
        # Get ftrack api module (as they are different per python version)
        ftrack_api = self.context.data["ftrackPythonModule"]

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
                hier_attr = hier_attr_by_key.get(key)
                # Use simple method if key is not hierarchical
                if not hier_attr:
                    assert (key in entity['custom_attributes']), (
                        'Missing custom attribute key: `{0}` in attrs: '
                        '`{1}`'.format(key, entity['custom_attributes'].keys())
                    )

                    entity['custom_attributes'][key] = custom_attributes[key]

                else:
                    # Use ftrack operations method to set hiearchical
                    # attribute value.
                    # - this is because there may be non hiearchical custom
                    #   attributes with different properties
                    entity_key = collections.OrderedDict()
                    entity_key["configuration_id"] = hier_attr["id"]
                    entity_key["entity_id"] = entity["id"]
                    self.session.recorded_operations.push(
                        ftrack_api.operation.UpdateEntityOperation(
                            "ContextCustomAttributeValue",
                            entity_key,
                            "value",
                            ftrack_api.symbol.NOT_SET,
                            custom_attributes[key]
                        )
                    )

                for instance in instances:
                    instance.data['ftrackEntity'] = entity

                try:
                    self.session.commit()
                except Exception:
                    tp, value, tb = sys.exc_info()
                    self.session.rollback()
                    self.session._configure_locations()
                    six.reraise(tp, value, tb)

            # TASKS
            tasks = entity_data.get('tasks', [])
            existing_tasks = []
            tasks_to_create = []
            for child in entity['children']:
                if child.entity_type.lower() == 'task':
                    existing_tasks.append(child['name'].lower())
                    # existing_tasks.append(child['type']['name'])

            for task_name in tasks:
                task_type = tasks[task_name]["type"]
                if task_name.lower() in existing_tasks:
                    print("Task {} already exists".format(task_name))
                    continue
                tasks_to_create.append((task_name, task_type))

            for task_name, task_type in tasks_to_create:
                self.create_task(
                    name=task_name,
                    task_type=task_type,
                    parent=entity
                )
                try:
                    self.session.commit()
                except Exception:
                    tp, value, tb = sys.exc_info()
                    self.session.rollback()
                    self.session._configure_locations()
                    six.reraise(tp, value, tb)

            # Incoming links.
            self.create_links(entity_data, entity)
            try:
                self.session.commit()
            except Exception:
                tp, value, tb = sys.exc_info()
                self.session.rollback()
                self.session._configure_locations()
                six.reraise(tp, value, tb)

            # Create notes.
            user = self.session.query(
                "User where username is \"{}\"".format(self.session.api_user)
            ).first()
            if user:
                for comment in entity_data.get("comments", []):
                    entity.create_note(comment, user)
            else:
                self.log.warning(
                    "Was not able to query current User {}".format(
                        self.session.api_user
                    )
                )
            try:
                self.session.commit()
            except Exception:
                tp, value, tb = sys.exc_info()
                self.session.rollback()
                self.session._configure_locations()
                six.reraise(tp, value, tb)

            # Import children.
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
                self.session._configure_locations()
                six.reraise(tp, value, tb)

        # Create new links.
        for input in entity_data.get("inputs", []):
            input_id = legacy_io.find_one({"_id": input})["data"]["ftrackId"]
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
            self.session._configure_locations()
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
            self.session._configure_locations()
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
            self.session._configure_locations()
            six.reraise(tp, value, tb)

    def auto_sync_on(self, project):

        project["custom_attributes"][CUST_ATTR_AUTO_SYNC] = True

        self.log.info("Ftrack autosync swithed on")

        try:
            self.session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            self.session.rollback()
            self.session._configure_locations()
            six.reraise(tp, value, tb)

    def _get_active_assets(self, context):
        """ Returns only asset dictionary.
            Usually the last part of deep dictionary which
            is not having any children
        """
        def get_pure_hierarchy_data(input_dict):
            input_dict_copy = deepcopy(input_dict)
            for key in input_dict.keys():
                self.log.debug("__ key: {}".format(key))
                # check if child key is available
                if input_dict[key].get("childs"):
                    # loop deeper
                    input_dict_copy[
                        key]["childs"] = get_pure_hierarchy_data(
                            input_dict[key]["childs"])
                elif key not in active_assets:
                    input_dict_copy.pop(key, None)
            return input_dict_copy

        hierarchy_context = context.data["hierarchyContext"]

        active_assets = []
        # filter only the active publishing insatnces
        for instance in context:
            if instance.data.get("publish") is False:
                continue

            if not instance.data.get("asset"):
                continue

            active_assets.append(instance.data["asset"])

        # remove duplicity in list
        active_assets = list(set(active_assets))
        self.log.debug("__ active_assets: {}".format(active_assets))

        return get_pure_hierarchy_data(hierarchy_context)
