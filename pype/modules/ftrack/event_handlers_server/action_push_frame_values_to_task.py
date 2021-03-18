import json
import collections
import ftrack_api
from pype.modules.ftrack.lib import ServerAction


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
    label = "Pype Admin"
    variant = "- Push Hierarchical values To Non-Hierarchical"

    hierarchy_entities_query = (
        "select id, parent_id from TypedContext where project_id is \"{}\""
    )
    entities_query = (
        "select id, name, parent_id, link from TypedContext"
        " where project_id is \"{}\" and object_type_id in ({})"
    )
    cust_attrs_query = (
        "select id, key, object_type_id, is_hierarchical, default"
        " from CustomAttributeConfiguration"
        " where key in ({})"
    )
    cust_attr_value_query = (
        "select value, entity_id from CustomAttributeValue"
        " where entity_id in ({}) and configuration_id in ({})"
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
            job["status"] = "done"
            session.commit()

            return result

        except Exception:
            session.rollback()
            job["status"] = "failed"
            session.commit()

            msg = "Pushing Custom attribute values to task Failed"
            self.log.warning(msg, exc_info=True)
            return {
                "success": False,
                "message": msg
            }

        finally:
            if job["status"] == "running":
                job["status"] = "failed"
                session.commit()

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

        entities = session.query(self.entities_query.format(
            project_entity["id"],
            self.join_query_keys(destination_object_type_ids)
        )).all()

        self.log.debug("Preparing whole project hierarchy by ids.")
        parent_id_by_entity_id = self.all_hierarchy_ids(
            session, project_entity
        )
        filtered_entities = self.filter_entities_by_selection(
            entities, selected_ids, parent_id_by_entity_id
        )
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

    def all_hierarchy_ids(self, session, project_entity):
        parent_id_by_entity_id = {}

        hierarchy_entities = session.query(
            self.hierarchy_entities_query.format(project_entity["id"])
        )
        for hierarchy_entity in hierarchy_entities:
            entity_id = hierarchy_entity["id"]
            parent_id = hierarchy_entity["parent_id"]
            parent_id_by_entity_id[entity_id] = parent_id
        return parent_id_by_entity_id

    def filter_entities_by_selection(
        self, entities, selected_ids, parent_id_by_entity_id
    ):
        filtered_entities = []
        for entity in entities:
            entity_id = entity["id"]
            if entity_id in selected_ids:
                filtered_entities.append(entity)
                continue

            parent_id = entity["parent_id"]
            while True:
                if parent_id in selected_ids:
                    filtered_entities.append(entity)
                    break

                parent_id = parent_id_by_entity_id.get(parent_id)
                if parent_id is None:
                    break

        return filtered_entities

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

        joined_entity_ids = self.join_query_keys(all_ids_with_parents)

        hier_attr_ids = self.join_query_keys(
            tuple(hier_attr["id"] for hier_attr in hier_attrs)
        )
        hier_attrs_key_by_id = {
            hier_attr["id"]: hier_attr["key"]
            for hier_attr in hier_attrs
        }
        call_expr = [{
            "action": "query",
            "expression": self.cust_attr_value_query.format(
                joined_entity_ids, hier_attr_ids
            )
        }]
        if hasattr(session, "call"):
            [values] = session.call(call_expr)
        else:
            [values] = session._call(call_expr)

        values_per_entity_id = {}
        for entity_id in all_ids_with_parents:
            values_per_entity_id[entity_id] = {}
            for key in hier_attrs_key_by_id.values():
                values_per_entity_id[entity_id][key] = None

        for item in values["data"]:
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
                _entity_key = collections.OrderedDict({
                    "configuration_id": configuration_id,
                    "entity_id": task_id
                })

                session.recorded_operations.push(
                    ftrack_api.operation.UpdateEntityOperation(
                        "ContextCustomAttributeValue",
                        _entity_key,
                        "value",
                        ftrack_api.symbol.NOT_SET,
                        value
                    )
                )
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

                    _entity_key = collections.OrderedDict({
                        "configuration_id": attr["id"],
                        "entity_id": entity_id
                    })

                    session.recorded_operations.push(
                        ftrack_api.operation.UpdateEntityOperation(
                            "ContextCustomAttributeValue",
                            _entity_key,
                            "value",
                            ftrack_api.symbol.NOT_SET,
                            value
                        )
                    )
        session.commit()


def register(session):
    PushHierValuesToNonHier(session).register()
