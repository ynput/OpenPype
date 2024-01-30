import sys
import collections
import six
from copy import deepcopy

import pyblish.api

from openpype.client import get_asset_by_id
from openpype.lib import filter_profiles
from openpype.pipeline import KnownPublishError

CUST_ATTR_GROUP = "openpype"


# Copy of `get_pype_attr` from openpype_modules.ftrack.lib
# TODO import from openpype's ftrack module when possible to not break Python 2
def get_pype_attr(session, split_hierarchical=True):
    custom_attributes = []
    hier_custom_attributes = []
    cust_attrs_query = (
        "select id, entity_type, object_type_id, is_hierarchical, default"
        " from CustomAttributeConfiguration"
        # Kept `pype` for Backwards Compatibility
        " where group.name in (\"pype\", \"ayon\", \"{}\")"
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
    label = "Integrate Hierarchy To Ftrack"
    families = ["shot"]
    hosts = [
        "hiero",
        "resolve",
        "standalonepublisher",
        "flame",
        "traypublisher"
    ]
    optional = False
    create_task_status_profiles = []

    def process(self, context):
        if "hierarchyContext" not in context.data:
            return

        hierarchy_context = self._get_active_assets(context)
        self.log.debug("__ hierarchy_context: {}".format(hierarchy_context))

        session = context.data["ftrackSession"]
        project_name = context.data["projectName"]
        project = session.query(
            'select id, full_name from Project where full_name is "{}"'.format(
                project_name
            )
        ).first()
        if not project:
            raise KnownPublishError(
                "Project \"{}\" was not found on ftrack.".format(project_name)
            )

        self.session = session
        self.ft_project = project
        self.task_types = self.get_all_task_types(project)
        self.task_statuses = self.get_task_statuses(project)

        # import ftrack hierarchy
        self.import_to_ftrack(context, project_name, hierarchy_context)

    def query_ftrack_entitites(self, session, ft_project):
        project_id = ft_project["id"]
        entities = session.query((
            "select id, name, parent_id"
            " from TypedContext where project_id is \"{}\""
        ).format(project_id)).all()

        entities_by_id = {}
        entities_by_parent_id = collections.defaultdict(list)
        for entity in entities:
            entities_by_id[entity["id"]] = entity
            parent_id = entity["parent_id"]
            entities_by_parent_id[parent_id].append(entity)

        ftrack_hierarchy = []
        ftrack_id_queue = collections.deque()
        ftrack_id_queue.append((project_id, ftrack_hierarchy))
        while ftrack_id_queue:
            item = ftrack_id_queue.popleft()
            ftrack_id, parent_list = item
            if ftrack_id == project_id:
                entity = ft_project
                name = entity["full_name"]
            else:
                entity = entities_by_id[ftrack_id]
                name = entity["name"]

            children = []
            parent_list.append({
                "name": name,
                "low_name": name.lower(),
                "entity": entity,
                "children": children,
            })
            for child in entities_by_parent_id[ftrack_id]:
                ftrack_id_queue.append((child["id"], children))
        return ftrack_hierarchy

    def find_matching_ftrack_entities(
        self, hierarchy_context, ftrack_hierarchy
    ):
        walk_queue = collections.deque()
        for entity_name, entity_data in hierarchy_context.items():
            walk_queue.append(
                (entity_name, entity_data, ftrack_hierarchy)
            )

        matching_ftrack_entities = []
        while walk_queue:
            item = walk_queue.popleft()
            entity_name, entity_data, ft_children = item
            matching_ft_child = None
            for ft_child in ft_children:
                if ft_child["low_name"] == entity_name.lower():
                    matching_ft_child = ft_child
                    break

            if matching_ft_child is None:
                continue

            entity = matching_ft_child["entity"]
            entity_data["ft_entity"] = entity
            matching_ftrack_entities.append(entity)

            hierarchy_children = entity_data.get("childs")
            if not hierarchy_children:
                continue

            for child_name, child_data in hierarchy_children.items():
                walk_queue.append(
                    (child_name, child_data, matching_ft_child["children"])
                )
        return matching_ftrack_entities

    def query_custom_attribute_values(self, session, entities, hier_attrs):
        attr_ids = {
            attr["id"]
            for attr in hier_attrs
        }
        entity_ids = {
            entity["id"]
            for entity in entities
        }
        output = {
            entity_id: {}
            for entity_id in entity_ids
        }
        if not attr_ids or not entity_ids:
            return {}

        joined_attr_ids = ",".join(
            ['"{}"'.format(attr_id) for attr_id in attr_ids]
        )

        # Query values in chunks
        chunk_size = int(5000 / len(attr_ids))
        # Make sure entity_ids is `list` for chunk selection
        entity_ids = list(entity_ids)
        results = []
        for idx in range(0, len(entity_ids), chunk_size):
            joined_entity_ids = ",".join([
                '"{}"'.format(entity_id)
                for entity_id in entity_ids[idx:idx + chunk_size]
            ])
            results.extend(
                session.query(
                    (
                        "select value, entity_id, configuration_id"
                        " from CustomAttributeValue"
                        " where entity_id in ({}) and configuration_id in ({})"
                    ).format(
                        joined_entity_ids,
                        joined_attr_ids
                    )
                ).all()
            )

        for result in results:
            attr_id = result["configuration_id"]
            entity_id = result["entity_id"]
            output[entity_id][attr_id] = result["value"]

        return output

    def import_to_ftrack(self, context, project_name, hierarchy_context):
        # Prequery hiearchical custom attributes
        hier_attrs = get_pype_attr(self.session)[1]
        hier_attr_by_key = {
            attr["key"]: attr
            for attr in hier_attrs
        }
        # Query user entity (for comments)
        user = self.session.query(
            "User where username is \"{}\"".format(self.session.api_user)
        ).first()
        if not user:
            self.log.warning(
                "Was not able to query current User {}".format(
                    self.session.api_user
                )
            )

        # Query ftrack hierarchy with parenting
        ftrack_hierarchy = self.query_ftrack_entitites(
            self.session, self.ft_project)

        # Fill ftrack entities to hierarchy context
        # - there is no need to query entities again
        matching_entities = self.find_matching_ftrack_entities(
            hierarchy_context, ftrack_hierarchy)
        # Query custom attribute values of each entity
        custom_attr_values_by_id = self.query_custom_attribute_values(
            self.session, matching_entities, hier_attrs)

        # Get ftrack api module (as they are different per python version)
        ftrack_api = context.data["ftrackPythonModule"]

        # Use queue of hierarchy items to process
        import_queue = collections.deque()
        for entity_name, entity_data in hierarchy_context.items():
            import_queue.append(
                (entity_name, entity_data, None)
            )

        while import_queue:
            item = import_queue.popleft()
            entity_name, entity_data, parent = item

            entity_type = entity_data['entity_type']
            self.log.debug(entity_data)

            entity = entity_data.get("ft_entity")
            if entity is None and entity_type.lower() == "project":
                raise AssertionError(
                    "Collected items are not in right order!"
                )

            # Create entity if not exists
            if entity is None:
                entity = self.session.create(entity_type, {
                    "name": entity_name,
                    "parent": parent
                })
                entity_data["ft_entity"] = entity

            # self.log.info('entity: {}'.format(dict(entity)))
            # CUSTOM ATTRIBUTES
            custom_attributes = entity_data.get('custom_attributes', {})
            instances = []
            for instance in context:
                instance_asset_name = instance.data.get("asset")
                if (
                    instance_asset_name
                    and instance_asset_name.lower() == entity["name"].lower()
                ):
                    instances.append(instance)

            for instance in instances:
                instance.data["ftrackEntity"] = entity

            for key, cust_attr_value in custom_attributes.items():
                if cust_attr_value is None:
                    continue

                hier_attr = hier_attr_by_key.get(key)
                # Use simple method if key is not hierarchical
                if not hier_attr:
                    if key not in entity["custom_attributes"]:
                        raise KnownPublishError((
                            "Missing custom attribute in ftrack with name '{}'"
                        ).format(key))

                    entity['custom_attributes'][key] = cust_attr_value
                    continue

                attr_id = hier_attr["id"]
                entity_values = custom_attr_values_by_id.get(entity["id"], {})
                # New value is defined by having id in values
                # - it can be set to 'None' (ftrack allows that using API)
                is_new_value = attr_id not in entity_values
                attr_value = entity_values.get(attr_id)

                # Use ftrack operations method to set hiearchical
                # attribute value.
                # - this is because there may be non hiearchical custom
                #   attributes with different properties
                entity_key = collections.OrderedDict((
                    ("configuration_id", hier_attr["id"]),
                    ("entity_id", entity["id"])
                ))
                op = None
                if is_new_value:
                    op = ftrack_api.operation.CreateEntityOperation(
                        "CustomAttributeValue",
                        entity_key,
                        {"value": cust_attr_value}
                    )

                elif attr_value != cust_attr_value:
                    op = ftrack_api.operation.UpdateEntityOperation(
                        "CustomAttributeValue",
                        entity_key,
                        "value",
                        attr_value,
                        cust_attr_value
                    )

                if op is not None:
                    self.session.recorded_operations.push(op)

            if self.session.recorded_operations:
                try:
                    self.session.commit()
                except Exception:
                    tp, value, tb = sys.exc_info()
                    self.session.rollback()
                    self.session._configure_locations()
                    six.reraise(tp, value, tb)

            # TASKS
            instances_by_task_name = collections.defaultdict(list)
            for instance in instances:
                task_name = instance.data.get("task")
                if task_name:
                    instances_by_task_name[task_name.lower()].append(instance)

            ftrack_status_by_task_id = context.data["ftrackStatusByTaskId"]
            tasks = entity_data.get('tasks', [])
            existing_tasks = []
            tasks_to_create = []
            for child in entity['children']:
                if child.entity_type.lower() == "task":
                    task_name_low = child["name"].lower()
                    existing_tasks.append(task_name_low)

                    for instance in instances_by_task_name[task_name_low]:
                        instance.data["ftrackTask"] = child

            for task_name in tasks:
                task_type = tasks[task_name]["type"]
                if task_name.lower() in existing_tasks:
                    print("Task {} already exists".format(task_name))
                    continue
                tasks_to_create.append((task_name, task_type))

            for task_name, task_type in tasks_to_create:
                task_entity = self.create_task(
                    task_name,
                    task_type,
                    entity,
                    ftrack_status_by_task_id
                )
                for instance in instances_by_task_name[task_name.lower()]:
                    instance.data["ftrackTask"] = task_entity

            # Incoming links.
            self.create_links(project_name, entity_data, entity)
            try:
                self.session.commit()
            except Exception:
                tp, value, tb = sys.exc_info()
                self.session.rollback()
                self.session._configure_locations()
                six.reraise(tp, value, tb)

            # Create notes.
            entity_comments = entity_data.get("comments")
            if user and entity_comments:
                for comment in entity_comments:
                    entity.create_note(comment, user)

                try:
                    self.session.commit()
                except Exception:
                    tp, value, tb = sys.exc_info()
                    self.session.rollback()
                    self.session._configure_locations()
                    six.reraise(tp, value, tb)

            # Import children.
            children = entity_data.get("childs")
            if not children:
                continue

            for entity_name, entity_data in children.items():
                import_queue.append(
                    (entity_name, entity_data, entity)
                )

    def create_links(self, project_name, entity_data, entity):
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
        for asset_id in entity_data.get("inputs", []):
            asset_doc = get_asset_by_id(project_name, asset_id)
            ftrack_id = None
            if asset_doc:
                ftrack_id = asset_doc["data"].get("ftrackId")
            if not ftrack_id:
                continue

            assetbuild = self.session.get("AssetBuild", ftrack_id)
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

    def get_task_statuses(self, project_entity):
        project_schema = project_entity["project_schema"]
        task_workflow_statuses = project_schema["_task_workflow"]["statuses"]
        return {
            status["id"]: status
            for status in task_workflow_statuses
        }

    def create_task(self, name, task_type, parent, ftrack_status_by_task_id):
        filter_data = {
            "task_names": name,
            "task_types": task_type
        }
        profile = filter_profiles(
            self.create_task_status_profiles,
            filter_data
        )
        status_id = None
        status_name = None
        if profile:
            status_name = profile["status_name"]
            status_name_low = status_name.lower()
            for _status_id, status in self.task_statuses.items():
                if status["name"].lower() == status_name_low:
                    status_id = _status_id
                    status_name = status["name"]
                    break

            if status_id is None:
                self.log.warning(
                    "Task status \"{}\" was not found".format(status_name)
                )

        task = self.session.create('Task', {
            'name': name,
            'parent': parent
        })
        # TODO not secured!!! - check if task_type exists
        self.log.info(task_type)
        self.log.info(self.task_types)
        task['type'] = self.task_types[task_type]
        if status_id is not None:
            task["status_id"] = status_id

        try:
            self.session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            self.session.rollback()
            self.session._configure_locations()
            six.reraise(tp, value, tb)

        if status_id is not None:
            ftrack_status_by_task_id[task["id"]] = None
        return task

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

        active_assets = set()
        # filter only the active publishing insatnces
        for instance in context:
            if instance.data.get("publish") is False:
                continue

            asset_name = instance.data.get("asset")
            if asset_name:
                active_assets.add(asset_name)

        # remove duplicity in list
        self.log.debug("__ active_assets: {}".format(list(active_assets)))

        return get_pure_hierarchy_data(hierarchy_context)
