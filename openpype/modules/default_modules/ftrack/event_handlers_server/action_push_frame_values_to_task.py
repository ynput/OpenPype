import sys
import json
import collections
import ftrack_api
from openpype_modules.ftrack.lib import (
    ServerAction,
    query_custom_attributes
)


class PushHierValuesToNonHier(ServerAction):
    """Action push hierarchical custom attribute values to non hierarchical.

    Hierarchical value is also pushed to their task entities.

    Action has 3 configurable attributes:
    - `role_list`: List of use roles that can discover the action.
    - `interest_attributes`: Keys of custom attributes that will be looking
        for to push values. Attribute key must have both custom attribute types
        hierarchical and on specific object type (entity type).
    - `interest_entity_types`: Entity types that will be in focus of pushing
        hierarchical to object type's custom attribute.

    EXAMPLE:
    * Before action
    |_ Project
      |_ Shot1
        - hierarchical custom attribute value: `frameStart`: 1001
        - custom attribute for `Shot`: frameStart: 1
        |_ Task1
            - hierarchical custom attribute value: `frameStart`: 10
            - custom attribute for `Task`: frameStart: 0

    * After action
    |_ Project
      |_ Shot1
        - hierarchical custom attribute value: `frameStart`: 1001
        - custom attribute for `Shot`: frameStart: 1001
        |_ Task1
            - hierarchical custom attribute value: `frameStart`: 1001
            - custom attribute for `Task`: frameStart: 1001
    """

    identifier = "admin.push_hier_values_to_non_hier"
    label = "OpenPype Admin"
    variant = "- Push Hierarchical values To Non-Hierarchical"

    entities_query_by_project = (
        "select id, parent_id, object_type_id from TypedContext"
        " where project_id is \"{}\""
    )
    cust_attrs_query = (
        "select id, key, object_type_id, is_hierarchical, default"
        " from CustomAttributeConfiguration"
        " where key in ({})"
    )

    # configurable
    settings_key = "sync_hier_entity_attributes"
    settings_enabled_key = "action_enabled"

    def discover(self, session, entities, event):
        """ Validation """
        # Check if selection is valid
        is_valid = False
        for ent in event["data"]["selection"]:
            # Ignore entities that are not tasks or projects
            if ent["entityType"].lower() in ("task", "show"):
                is_valid = True
                break

        if is_valid:
            is_valid = self.valid_roles(session, entities, event)
        return is_valid

    def launch(self, session, entities, event):
        self.log.debug("{}: Creating job".format(self.label))

        user_entity = session.query(
            "User where id is {}".format(event["source"]["user"]["id"])
        ).one()
        job = session.create("Job", {
            "user": user_entity,
            "status": "running",
            "data": json.dumps({
                "description": "Propagation of Frame attribute values to task."
            })
        })
        session.commit()

        try:
            result = self.propagate_values(session, event, entities)

        except Exception as exc:
            msg = "Pushing Custom attribute values to task Failed"

            self.log.warning(msg, exc_info=True)

            session.rollback()

            description = "{} (Download traceback)".format(msg)
            self.add_traceback_to_job(
                job, session, sys.exc_info(), description
            )

            return {
                "success": False,
                "message": "Error: {}".format(str(exc))
            }

        job["status"] = "done"
        session.commit()

        return result

    def attrs_configurations(self, session, object_ids, interest_attributes):
        attrs = session.query(self.cust_attrs_query.format(
            self.join_query_keys(interest_attributes),
            self.join_query_keys(object_ids)
        )).all()

        output = {}
        hiearchical = []
        for attr in attrs:
            if attr["is_hierarchical"]:
                hiearchical.append(attr)
                continue
            obj_id = attr["object_type_id"]
            if obj_id not in output:
                output[obj_id] = []
            output[obj_id].append(attr)
        return output, hiearchical

    def propagate_values(self, session, event, selected_entities):
        ftrack_settings = self.get_ftrack_settings(
            session, event, selected_entities
        )
        action_settings = (
            ftrack_settings[self.settings_frack_subkey][self.settings_key]
        )

        project_entity = self.get_project_from_entity(selected_entities[0])
        selected_ids = [entity["id"] for entity in selected_entities]

        self.log.debug("Querying project's entities \"{}\".".format(
            project_entity["full_name"]
        ))
        interest_entity_types = tuple(
            ent_type.lower()
            for ent_type in action_settings["interest_entity_types"]
        )
        all_object_types = session.query("ObjectType").all()
        object_types_by_low_name = {
            object_type["name"].lower(): object_type
            for object_type in all_object_types
        }

        task_object_type = object_types_by_low_name["task"]
        destination_object_types = [task_object_type]
        for ent_type in interest_entity_types:
            obj_type = object_types_by_low_name.get(ent_type)
            if obj_type and obj_type not in destination_object_types:
                destination_object_types.append(obj_type)

        destination_object_type_ids = set(
            obj_type["id"]
            for obj_type in destination_object_types
        )

        interest_attributes = action_settings["interest_attributes"]
        # Find custom attributes definitions
        attrs_by_obj_id, hier_attrs = self.attrs_configurations(
            session, destination_object_type_ids, interest_attributes
        )
        # Filter destination object types if they have any object specific
        # custom attribute
        for obj_id in tuple(destination_object_type_ids):
            if obj_id not in attrs_by_obj_id:
                destination_object_type_ids.remove(obj_id)

        if not destination_object_type_ids:
            # TODO report that there are not matching custom attributes
            return {
                "success": True,
                "message": "Nothing has changed."
            }

        (
            parent_id_by_entity_id,
            filtered_entities
        ) = self.all_hierarchy_entities(
            session,
            selected_ids,
            project_entity,
            destination_object_type_ids
        )

        self.log.debug("Preparing whole project hierarchy by ids.")

        entities_by_obj_id = {
            obj_id: []
            for obj_id in destination_object_type_ids
        }

        self.log.debug("Filtering Task entities.")
        focus_entity_ids = []
        non_task_entity_ids = []
        task_entity_ids = []
        for entity in filtered_entities:
            entity_id = entity["id"]
            focus_entity_ids.append(entity_id)
            if entity.entity_type.lower() == "task":
                task_entity_ids.append(entity_id)
            else:
                non_task_entity_ids.append(entity_id)

            obj_id = entity["object_type_id"]
            entities_by_obj_id[obj_id].append(entity_id)

        if not non_task_entity_ids:
            return {
                "success": True,
                "message": "Nothing to do in your selection."
            }

        self.log.debug("Getting Hierarchical custom attribute values parents.")
        hier_values_by_entity_id = self.get_hier_values(
            session,
            hier_attrs,
            non_task_entity_ids,
            parent_id_by_entity_id
        )

        self.log.debug("Setting parents' values to task.")
        self.set_task_attr_values(
            session,
            hier_attrs,
            task_entity_ids,
            hier_values_by_entity_id,
            parent_id_by_entity_id
        )

        self.log.debug("Setting values to entities themselves.")
        self.push_values_to_entities(
            session,
            entities_by_obj_id,
            attrs_by_obj_id,
            hier_values_by_entity_id
        )

        return True

    def all_hierarchy_entities(
        self,
        session,
        selected_ids,
        project_entity,
        destination_object_type_ids
    ):
        selected_ids = set(selected_ids)

        filtered_entities = []
        parent_id_by_entity_id = {}
        # Query is simple if project is in selection
        if project_entity["id"] in selected_ids:
            entities = session.query(
                self.entities_query_by_project.format(project_entity["id"])
            ).all()

            for entity in entities:
                if entity["object_type_id"] in destination_object_type_ids:
                    filtered_entities.append(entity)
                entity_id = entity["id"]
                parent_id_by_entity_id[entity_id] = entity["parent_id"]
            return parent_id_by_entity_id, filtered_entities

        # Query selection and get it's link to be able calculate parentings
        entities_with_link = session.query((
            "select id, parent_id, link, object_type_id"
            " from TypedContext where id in ({})"
        ).format(self.join_query_keys(selected_ids))).all()

        # Process and store queried entities and store all lower entities to
        #   `bottom_ids`
        # - bottom_ids should not contain 2 ids where one is parent of second
        bottom_ids = set(selected_ids)
        for entity in entities_with_link:
            if entity["object_type_id"] in destination_object_type_ids:
                filtered_entities.append(entity)
            children_id = None
            for idx, item in enumerate(reversed(entity["link"])):
                item_id = item["id"]
                if idx > 0 and item_id in bottom_ids:
                    bottom_ids.remove(item_id)

                if children_id is not None:
                    parent_id_by_entity_id[children_id] = item_id

                children_id = item_id

        # Query all children of selection per one hierarchy level and process
        #   their data the same way as selection but parents are already known
        chunk_size = 100
        while bottom_ids:
            child_entities = []
            # Query entities in chunks
            entity_ids = list(bottom_ids)
            for idx in range(0, len(entity_ids), chunk_size):
                _entity_ids = entity_ids[idx:idx + chunk_size]
                child_entities.extend(session.query((
                    "select id, parent_id, object_type_id from"
                    " TypedContext where parent_id in ({})"
                ).format(self.join_query_keys(_entity_ids))).all())

            bottom_ids = set()
            for entity in child_entities:
                entity_id = entity["id"]
                parent_id_by_entity_id[entity_id] = entity["parent_id"]
                bottom_ids.add(entity_id)
                if entity["object_type_id"] in destination_object_type_ids:
                    filtered_entities.append(entity)

        return parent_id_by_entity_id, filtered_entities

    def get_hier_values(
        self,
        session,
        hier_attrs,
        focus_entity_ids,
        parent_id_by_entity_id
    ):
        all_ids_with_parents = set()
        for entity_id in focus_entity_ids:
            all_ids_with_parents.add(entity_id)
            _entity_id = entity_id
            while True:
                parent_id = parent_id_by_entity_id.get(_entity_id)
                if (
                    not parent_id
                    or parent_id in all_ids_with_parents
                ):
                    break
                all_ids_with_parents.add(parent_id)
                _entity_id = parent_id

        hier_attr_ids = tuple(hier_attr["id"] for hier_attr in hier_attrs)
        hier_attrs_key_by_id = {
            hier_attr["id"]: hier_attr["key"]
            for hier_attr in hier_attrs
        }

        values_per_entity_id = {}
        for entity_id in all_ids_with_parents:
            values_per_entity_id[entity_id] = {}
            for key in hier_attrs_key_by_id.values():
                values_per_entity_id[entity_id][key] = None

        values = query_custom_attributes(
            session, all_ids_with_parents, hier_attr_ids, True
        )
        for item in values:
            entity_id = item["entity_id"]
            key = hier_attrs_key_by_id[item["configuration_id"]]

            values_per_entity_id[entity_id][key] = item["value"]

        output = {}
        for entity_id in focus_entity_ids:
            output[entity_id] = {}
            for key in hier_attrs_key_by_id.values():
                value = values_per_entity_id[entity_id][key]
                tried_ids = set()
                if value is None:
                    tried_ids.add(entity_id)
                    _entity_id = entity_id
                    while value is None:
                        parent_id = parent_id_by_entity_id.get(_entity_id)
                        if not parent_id:
                            break
                        value = values_per_entity_id[parent_id][key]
                        if value is not None:
                            break
                        _entity_id = parent_id
                        tried_ids.add(parent_id)

                if value is not None:
                    for ent_id in tried_ids:
                        values_per_entity_id[ent_id][key] = value

                output[entity_id][key] = value
        return output

    def set_task_attr_values(
        self,
        session,
        hier_attrs,
        task_entity_ids,
        hier_values_by_entity_id,
        parent_id_by_entity_id
    ):
        hier_attr_id_by_key = {
            attr["key"]: attr["id"]
            for attr in hier_attrs
        }
        for task_id in task_entity_ids:
            parent_id = parent_id_by_entity_id.get(task_id) or {}
            parent_values = hier_values_by_entity_id.get(parent_id)
            if not parent_values:
                continue

            hier_values_by_entity_id[task_id] = {}
            for key, value in parent_values.items():
                hier_values_by_entity_id[task_id][key] = value
                configuration_id = hier_attr_id_by_key[key]
                _entity_key = collections.OrderedDict([
                    ("configuration_id", configuration_id),
                    ("entity_id", task_id)
                ])

                session.recorded_operations.push(
                    ftrack_api.operation.UpdateEntityOperation(
                        "ContextCustomAttributeValue",
                        _entity_key,
                        "value",
                        ftrack_api.symbol.NOT_SET,
                        value
                    )
                )
                if len(session.recorded_operations) > 100:
                    session.commit()

        session.commit()

    def push_values_to_entities(
        self,
        session,
        entities_by_obj_id,
        attrs_by_obj_id,
        hier_values_by_entity_id
    ):
        for object_id, entity_ids in entities_by_obj_id.items():
            attrs = attrs_by_obj_id.get(object_id)
            if not attrs or not entity_ids:
                continue

            for attr in attrs:
                for entity_id in entity_ids:
                    value = (
                        hier_values_by_entity_id
                        .get(entity_id, {})
                        .get(attr["key"])
                    )
                    if value is None:
                        continue

                    _entity_key = collections.OrderedDict([
                        ("configuration_id", attr["id"]),
                        ("entity_id", entity_id)
                    ])

                    session.recorded_operations.push(
                        ftrack_api.operation.UpdateEntityOperation(
                            "ContextCustomAttributeValue",
                            _entity_key,
                            "value",
                            ftrack_api.symbol.NOT_SET,
                            value
                        )
                    )
                    if len(session.recorded_operations) > 100:
                        session.commit()

        session.commit()


def register(session):
    PushHierValuesToNonHier(session).register()
