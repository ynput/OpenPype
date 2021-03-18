import collections
import datetime

import ftrack_api
from pype.modules.ftrack.lib import BaseEvent


class PushFrameValuesToTaskEvent(BaseEvent):
    # Ignore event handler by default
    cust_attrs_query = (
        "select id, key, object_type_id, is_hierarchical, default"
        " from CustomAttributeConfiguration"
        " where key in ({}) and"
        " (object_type_id in ({}) or is_hierarchical is true)"
    )

    cust_attr_query = (
        "select value, entity_id from ContextCustomAttributeValue "
        "where entity_id in ({}) and configuration_id in ({})"
    )

    _cached_task_object_id = None
    _cached_interest_object_ids = None
    _cached_user_id = None
    _cached_changes = []
    _max_delta = 30

    settings_key = "sync_hier_entity_attributes"

    def session_user_id(self, session):
        if self._cached_user_id is None:
            user = session.query(
                "User where username is \"{}\"".format(session.api_user)
            ).one()
            self._cached_user_id = user["id"]
        return self._cached_user_id

    def launch(self, session, event):
        filtered_entities_info = self.filter_entities_info(event)
        if not filtered_entities_info:
            return

        for project_id, entities_info in filtered_entities_info.items():
            self.process_by_project(session, event, project_id, entities_info)

    def filter_entities_info(self, event):
        # Filter if event contain relevant data
        entities_info = event["data"].get("entities")
        if not entities_info:
            return

        entities_info_by_project_id = {}
        for entity_info in entities_info:
            # Care only about tasks
            if entity_info.get("entityType") != "task":
                continue

            # Skip `Task` entity type
            if entity_info["entity_type"].lower() == "task":
                continue

            # Care only about changes of status
            changes = entity_info.get("changes")
            if not changes:
                continue

            # Get project id from entity info
            project_id = None
            for parent_item in reversed(entity_info["parents"]):
                if parent_item["entityType"] == "show":
                    project_id = parent_item["entityId"]
                    break

            if project_id is None:
                continue

            if project_id not in entities_info_by_project_id:
                entities_info_by_project_id[project_id] = []
            entities_info_by_project_id[project_id].append(entity_info)

        return entities_info_by_project_id

    def process_by_project(self, session, event, project_id, entities_info):
        project_name = self.get_project_name_from_event(
            session, event, project_id
        )
        # Load settings
        project_settings = self.get_project_settings_from_event(
            event, project_name
        )
        # Load status mapping from presets
        event_settings = (
            project_settings
            ["ftrack"]
            ["events"]
            ["sync_hier_entity_attributes"]
        )
        # Skip if event is not enabled
        if not event_settings["enabled"]:
            self.log.debug("Project \"{}\" has disabled {}".format(
                project_name, self.__class__.__name__
            ))
            return

        interest_attributes = event_settings["interest_attributes"]
        if not interest_attributes:
            self.log.info((
                "Project \"{}\" does not have filled 'interest_attributes',"
                " skipping."
            ))
            return
        interest_entity_types = event_settings["interest_entity_types"]
        if not interest_entity_types:
            self.log.info((
                "Project \"{}\" does not have filled 'interest_entity_types',"
                " skipping."
            ))
            return

        # Filter entities info with changes
        interesting_data, changed_keys_by_object_id = self.filter_changes(
            session, event, entities_info, interest_attributes
        )
        if not interesting_data:
            return

        # Prepare object types
        object_types = session.query("select id, name from ObjectType").all()
        object_types_by_name = {}
        for object_type in object_types:
            name_low = object_type["name"].lower()
            object_types_by_name[name_low] = object_type

        # Prepare task object id
        task_object_id = object_types_by_name["task"]["id"]

        # Collect object type ids based on settings
        interest_object_ids = []
        for entity_type in interest_entity_types:
            _entity_type = entity_type.lower()
            object_type = object_types_by_name.get(_entity_type)
            if not object_type:
                self.log.warning("Couldn't find object type \"{}\"".format(
                    entity_type
                ))

            interest_object_ids.append(object_type["id"])

        # Query entities by filtered data and object ids
        entities = self.get_entities(
            session, interesting_data, interest_object_ids
        )
        if not entities:
            return

        # Pop not found entities from interesting data
        entity_ids = set(
            entity["id"]
            for entity in entities
        )
        for entity_id in tuple(interesting_data.keys()):
            if entity_id not in entity_ids:
                interesting_data.pop(entity_id)

        # Add task object type to list
        attr_obj_ids = list(interest_object_ids)
        attr_obj_ids.append(task_object_id)

        attrs_by_obj_id, hier_attrs = self.attrs_configurations(
            session, attr_obj_ids, interest_attributes
        )

        task_attrs = attrs_by_obj_id.get(task_object_id)

        changed_keys = set()
        # Skip keys that are not both in hierachical and type specific
        for object_id, keys in changed_keys_by_object_id.items():
            changed_keys |= set(keys)
            object_id_attrs = attrs_by_obj_id.get(object_id)
            for key in keys:
                if key not in hier_attrs:
                    attrs_by_obj_id[object_id].pop(key)
                    continue

                if (
                    (not object_id_attrs or key not in object_id_attrs)
                    and (not task_attrs or key not in task_attrs)
                ):
                    hier_attrs.pop(key)

        # Clean up empty values
        for key, value in tuple(attrs_by_obj_id.items()):
            if not value:
                attrs_by_obj_id.pop(key)

        if not attrs_by_obj_id:
            self.log.warning((
                "There is not created Custom Attributes {} "
                " for entity types: {}"
            ).format(
                self.join_query_keys(interest_attributes),
                self.join_query_keys(interest_entity_types)
            ))
            return

        # Prepare task entities
        task_entities = []
        # If task entity does not contain changed attribute then skip
        if task_attrs:
            task_entities = self.get_task_entities(session, interesting_data)

        task_entity_ids = set()
        parent_id_by_task_id = {}
        for task_entity in task_entities:
            task_id = task_entity["id"]
            task_entity_ids.add(task_id)
            parent_id_by_task_id[task_id] = task_entity["parent_id"]

        self.finalize(
            session, interesting_data,
            changed_keys, attrs_by_obj_id, hier_attrs,
            task_entity_ids, parent_id_by_task_id
        )

    def finalize(
        self, session, interesting_data,
        changed_keys, attrs_by_obj_id, hier_attrs,
        task_entity_ids, parent_id_by_task_id
    ):
        attr_id_to_key = {}
        for attr_confs in attrs_by_obj_id.values():
            for key in changed_keys:
                custom_attr_id = attr_confs.get(key)
                if custom_attr_id:
                    attr_id_to_key[custom_attr_id] = key

        for key in changed_keys:
            custom_attr_id = hier_attrs.get(key)
            if custom_attr_id:
                attr_id_to_key[custom_attr_id] = key

        entity_ids = (
            set(interesting_data.keys()) | task_entity_ids
        )
        attr_ids = set(attr_id_to_key.keys())

        current_values_by_id = self.current_values(
            session, attr_ids, entity_ids, task_entity_ids, hier_attrs
        )

        for entity_id, current_values in current_values_by_id.items():
            parent_id = parent_id_by_task_id.get(entity_id)
            if not parent_id:
                parent_id = entity_id
            values = interesting_data[parent_id]

            for attr_id, old_value in current_values.items():
                attr_key = attr_id_to_key.get(attr_id)
                if not attr_key:
                    continue

                # Convert new value from string
                new_value = values.get(attr_key)
                if new_value is not None and old_value is not None:
                    try:
                        new_value = type(old_value)(new_value)
                    except Exception:
                        self.log.warning((
                            "Couldn't convert from {} to {}."
                            " Skipping update values."
                        ).format(type(new_value), type(old_value)))
                if new_value == old_value:
                    continue

                entity_key = collections.OrderedDict()
                entity_key["configuration_id"] = attr_id
                entity_key["entity_id"] = entity_id
                self._cached_changes.append({
                    "attr_key": attr_key,
                    "entity_id": entity_id,
                    "value": new_value,
                    "time": datetime.datetime.now()
                })
                if new_value is None:
                    op = ftrack_api.operation.DeleteEntityOperation(
                        "CustomAttributeValue",
                        entity_key
                    )
                else:
                    op = ftrack_api.operation.UpdateEntityOperation(
                        "ContextCustomAttributeValue",
                        entity_key,
                        "value",
                        ftrack_api.symbol.NOT_SET,
                        new_value
                    )

                session.recorded_operations.push(op)
                self.log.info((
                    "Changing Custom Attribute \"{}\" to value"
                    " \"{}\" on entity: {}"
                ).format(attr_key, new_value, entity_id))
            try:
                session.commit()
            except Exception:
                session.rollback()
                self.log.warning("Changing of values failed.", exc_info=True)

    def filter_changes(
        self, session, event, entities_info, interest_attributes
    ):
        session_user_id = self.session_user_id(session)
        user_data = event["data"].get("user")
        changed_by_session = False
        if user_data and user_data.get("userid") == session_user_id:
            changed_by_session = True

        current_time = datetime.datetime.now()

        interesting_data = {}
        changed_keys_by_object_id = {}
        for entity_info in entities_info:
            # Care only about changes if specific keys
            entity_changes = {}
            changes = entity_info["changes"]
            for key in interest_attributes:
                if key in changes:
                    entity_changes[key] = changes[key]["new"]

            entity_id = entity_info["entityId"]
            if changed_by_session:
                for key, new_value in tuple(entity_changes.items()):
                    for cached in tuple(self._cached_changes):
                        if (
                            cached["entity_id"] != entity_id
                            or cached["attr_key"] != key
                        ):
                            continue

                        cached_value = cached["value"]
                        try:
                            new_value = type(cached_value)(new_value)
                        except Exception:
                            pass

                        if cached_value == new_value:
                            self._cached_changes.remove(cached)
                            entity_changes.pop(key)
                            break

                        delta = (current_time - cached["time"]).seconds
                        if delta > self._max_delta:
                            self._cached_changes.remove(cached)

            if not entity_changes:
                continue

            entity_id = entity_info["entityId"]
            object_id = entity_info["objectTypeId"]
            interesting_data[entity_id] = entity_changes
            if object_id not in changed_keys_by_object_id:
                changed_keys_by_object_id[object_id] = set()
            changed_keys_by_object_id[object_id] |= set(entity_changes.keys())

        return interesting_data, changed_keys_by_object_id

    def current_values(
        self, session, attr_ids, entity_ids, task_entity_ids, hier_attrs
    ):
        current_values_by_id = {}
        if not attr_ids or not entity_ids:
            return current_values_by_id
        joined_conf_ids = self.join_query_keys(attr_ids)
        joined_entity_ids = self.join_query_keys(entity_ids)

        call_expr = [{
            "action": "query",
            "expression": self.cust_attr_query.format(
                joined_entity_ids, joined_conf_ids
            )
        }]
        if hasattr(session, "call"):
            [values] = session.call(call_expr)
        else:
            [values] = session._call(call_expr)

        for item in values["data"]:
            entity_id = item["entity_id"]
            attr_id = item["configuration_id"]
            if entity_id in task_entity_ids and attr_id in hier_attrs:
                continue

            if entity_id not in current_values_by_id:
                current_values_by_id[entity_id] = {}
            current_values_by_id[entity_id][attr_id] = item["value"]
        return current_values_by_id

    def get_entities(self, session, interesting_data, interest_object_ids):
        return session.query((
            "select id from TypedContext"
            " where id in ({}) and object_type_id in ({})"
        ).format(
            self.join_query_keys(interesting_data.keys()),
            self.join_query_keys(interest_object_ids)
        )).all()

    def get_task_entities(self, session, interesting_data):
        return session.query(
            "select id, parent_id from Task where parent_id in ({})".format(
                self.join_query_keys(interesting_data.keys())
            )
        ).all()

    def attrs_configurations(self, session, object_ids, interest_attributes):
        attrs = session.query(self.cust_attrs_query.format(
            self.join_query_keys(interest_attributes),
            self.join_query_keys(object_ids)
        )).all()

        output = {}
        hiearchical = {}
        for attr in attrs:
            if attr["is_hierarchical"]:
                hiearchical[attr["key"]] = attr["id"]
                continue
            obj_id = attr["object_type_id"]
            if obj_id not in output:
                output[obj_id] = {}
            output[obj_id][attr["key"]] = attr["id"]
        return output, hiearchical


def register(session):
    PushFrameValuesToTaskEvent(session).register()
