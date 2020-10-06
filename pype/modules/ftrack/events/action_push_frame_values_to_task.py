import json
import collections
import ftrack_api
from pype.modules.ftrack.lib import BaseAction


class PushFrameValuesToTaskAction(BaseAction):
    """Action for testing purpose or as base for new actions."""

    # Ignore event handler by default
    ignore_me = True

    identifier = "admin.push_frame_values_to_task"
    label = "Pype Admin"
    variant = "- Push Frame values to Task"

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

    pushing_entity_types = {"Shot"}
    hierarchical_custom_attribute_keys = {"frameStart", "frameEnd"}
    custom_attribute_mapping = {
        "frameStart": "fstart",
        "frameEnd": "fend"
    }
    discover_role_list = {"Pypeclub", "Administrator", "Project Manager"}

    def register(self):
        modified_role_names = set()
        for role_name in self.discover_role_list:
            modified_role_names.add(role_name.lower())
        self.discover_role_list = modified_role_names

        self.session.event_hub.subscribe(
            "topic=ftrack.action.discover",
            self._discover,
            priority=self.priority
        )

        launch_subscription = (
            "topic=ftrack.action.launch and data.actionIdentifier={0}"
        ).format(self.identifier)
        self.session.event_hub.subscribe(launch_subscription, self._launch)

    def discover(self, session, entities, event):
        """ Validation """
        # Check if selection is valid
        valid_selection = False
        for ent in event["data"]["selection"]:
            # Ignore entities that are not tasks or projects
            if ent["entityType"].lower() == "show":
                valid_selection = True
                break

        if not valid_selection:
            return False

        # Get user and check his roles
        user_id = event.get("source", {}).get("user", {}).get("id")
        if not user_id:
            return False

        user = session.query("User where id is \"{}\"".format(user_id)).first()
        if not user:
            return False

        for role in user["user_security_roles"]:
            lowered_role = role["security_role"]["name"].lower()
            if lowered_role in self.discover_role_list:
                return True
        return False

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
            project_entity = self.get_project_from_entity(entities[0])
            result = self.propagate_values(session, project_entity, event)
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

    def task_attributes(self, session):
        task_object_type = session.query(
            "ObjectType where name is \"Task\""
        ).one()

        hier_attr_names = list(
            self.custom_attribute_mapping.keys()
        )
        entity_type_specific_names = list(
            self.custom_attribute_mapping.values()
        )
        joined_keys = self.join_keys(
            hier_attr_names + entity_type_specific_names
        )
        attribute_entities = session.query(
            self.cust_attrs_query.format(joined_keys)
        ).all()

        hier_attrs = []
        task_attrs = {}
        for attr in attribute_entities:
            attr_key = attr["key"]
            if attr["is_hierarchical"]:
                if attr_key in hier_attr_names:
                    hier_attrs.append(attr)
            elif attr["object_type_id"] == task_object_type["id"]:
                if attr_key in entity_type_specific_names:
                    task_attrs[attr_key] = attr["id"]
        return task_attrs, hier_attrs

    def join_keys(self, items):
        return ",".join(["\"{}\"".format(item) for item in items])

    def propagate_values(self, session, project_entity, event):
        self.log.debug("Querying project's entities \"{}\".".format(
            project_entity["full_name"]
        ))
        pushing_entity_types = tuple(
            ent_type.lower()
            for ent_type in self.pushing_entity_types
        )
        destination_object_types = []
        all_object_types = session.query("ObjectType").all()
        for object_type in all_object_types:
            lowered_name = object_type["name"].lower()
            if (
                lowered_name == "task"
                or lowered_name in pushing_entity_types
            ):
                destination_object_types.append(object_type)

        destination_object_type_ids = tuple(
            obj_type["id"]
            for obj_type in destination_object_types
        )
        entities = session.query(self.entities_query.format(
            project_entity["id"],
            self.join_keys(destination_object_type_ids)
        )).all()

        entities_by_id = {
            entity["id"]: entity
            for entity in entities
        }

        self.log.debug("Filtering Task entities.")
        task_entities_by_parent_id = collections.defaultdict(list)
        non_task_entities = []
        non_task_entity_ids = []
        for entity in entities:
            if entity.entity_type.lower() != "task":
                non_task_entities.append(entity)
                non_task_entity_ids.append(entity["id"])
                continue

            parent_id = entity["parent_id"]
            if parent_id in entities_by_id:
                task_entities_by_parent_id[parent_id].append(entity)

        task_attr_id_by_keys, hier_attrs = self.task_attributes(session)

        self.log.debug("Getting Custom attribute values from tasks' parents.")
        hier_values_by_entity_id = self.get_hier_values(
            session,
            hier_attrs,
            non_task_entity_ids
        )

        self.log.debug("Setting parents' values to task.")
        task_missing_keys = self.set_task_attr_values(
            session,
            task_entities_by_parent_id,
            hier_values_by_entity_id,
            task_attr_id_by_keys
        )

        self.log.debug("Setting values to entities themselves.")
        missing_keys_by_object_name = self.push_values_to_entities(
            session,
            non_task_entities,
            hier_values_by_entity_id
        )
        if task_missing_keys:
            missing_keys_by_object_name["Task"] = task_missing_keys
        if missing_keys_by_object_name:
            self.report(missing_keys_by_object_name, event)
        return True

    def report(self, missing_keys_by_object_name, event):
        splitter = {"type": "label", "value": "---"}

        title = "Push Custom Attribute values report:"

        items = []
        items.append({
            "type": "label",
            "value": "# Pushing values was not complete"
        })
        items.append({
            "type": "label",
            "value": (
                "<p>It was due to missing custom"
                " attribute configurations for specific entity type/s."
                " These configurations are not created automatically.</p>"
            )
        })

        log_message_items = []
        log_message_item_template = (
            "Entity type \"{}\" does not have created Custom Attribute/s: {}"
        )
        for object_name, missing_attr_names in (
            missing_keys_by_object_name.items()
        ):
            log_message_items.append(log_message_item_template.format(
                object_name, self.join_keys(missing_attr_names)
            ))

            items.append(splitter)
            items.append({
                "type": "label",
                "value": "## Entity type: {}".format(object_name)
            })

            items.append({
                "type": "label",
                "value": "<p>{}</p>".format("<br>".join(missing_attr_names))
            })

        self.log.warning((
            "Couldn't finish pushing attribute values because"
            " few entity types miss Custom attribute configurations:\n{}"
        ).format("\n".join(log_message_items)))

        self.show_interface(items, title, event)

    def get_hier_values(self, session, hier_attrs, focus_entity_ids):
        joined_entity_ids = self.join_keys(focus_entity_ids)
        hier_attr_ids = self.join_keys(
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
        for item in values["data"]:
            entity_id = item["entity_id"]
            key = hier_attrs_key_by_id[item["configuration_id"]]

            if entity_id not in values_per_entity_id:
                values_per_entity_id[entity_id] = {}
            value = item["value"]
            if value is not None:
                values_per_entity_id[entity_id][key] = value

        output = {}
        for entity_id in focus_entity_ids:
            value = values_per_entity_id.get(entity_id)
            if value:
                output[entity_id] = value

        return output

    def set_task_attr_values(
        self,
        session,
        task_entities_by_parent_id,
        hier_values_by_entity_id,
        task_attr_id_by_keys
    ):
        missing_keys = set()
        for parent_id, values in hier_values_by_entity_id.items():
            task_entities = task_entities_by_parent_id[parent_id]
            for hier_key, value in values.items():
                key = self.custom_attribute_mapping[hier_key]
                if key not in task_attr_id_by_keys:
                    missing_keys.add(key)
                    continue

                for task_entity in task_entities:
                    _entity_key = collections.OrderedDict({
                        "configuration_id": task_attr_id_by_keys[key],
                        "entity_id": task_entity["id"]
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

        return missing_keys

    def push_values_to_entities(
        self,
        session,
        non_task_entities,
        hier_values_by_entity_id
    ):
        object_types = session.query(
            "ObjectType where name in ({})".format(
                self.join_keys(self.pushing_entity_types)
            )
        ).all()
        object_type_names_by_id = {
            object_type["id"]: object_type["name"]
            for object_type in object_types
        }
        joined_keys = self.join_keys(
             self.custom_attribute_mapping.values()
        )
        attribute_entities = session.query(
            self.cust_attrs_query.format(joined_keys)
        ).all()

        attrs_by_obj_id = {}
        for attr in attribute_entities:
            if attr["is_hierarchical"]:
                continue

            obj_id = attr["object_type_id"]
            if obj_id not in object_type_names_by_id:
                continue

            if obj_id not in attrs_by_obj_id:
                attrs_by_obj_id[obj_id] = {}

            attr_key = attr["key"]
            attrs_by_obj_id[obj_id][attr_key] = attr["id"]

        entities_by_obj_id = collections.defaultdict(list)
        for entity in non_task_entities:
            entities_by_obj_id[entity["object_type_id"]].append(entity)

        missing_keys_by_object_id = collections.defaultdict(set)
        for obj_type_id, attr_keys in attrs_by_obj_id.items():
            entities = entities_by_obj_id.get(obj_type_id)
            if not entities:
                continue

            for entity in entities:
                values = hier_values_by_entity_id.get(entity["id"])
                if not values:
                    continue

                for hier_key, value in values.items():
                    key = self.custom_attribute_mapping[hier_key]
                    if key not in attr_keys:
                        missing_keys_by_object_id[obj_type_id].add(key)
                        continue

                    _entity_key = collections.OrderedDict({
                        "configuration_id": attr_keys[key],
                        "entity_id": entity["id"]
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

        missing_keys_by_object_name = {}
        for obj_id, missing_keys in missing_keys_by_object_id.items():
            obj_name = object_type_names_by_id[obj_id]
            missing_keys_by_object_name[obj_name] = missing_keys

        return missing_keys_by_object_name


def register(session, plugins_presets={}):
    PushFrameValuesToTaskAction(session, plugins_presets).register()
