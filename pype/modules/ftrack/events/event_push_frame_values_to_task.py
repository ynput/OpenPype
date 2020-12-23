import collections
import datetime

import ftrack_api
from pype.modules.ftrack import BaseEvent


class PushFrameValuesToTaskEvent(BaseEvent):
    # Ignore event handler by default
    ignore_me = True

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

    # Configrable (lists)
    interest_entity_types = {"Shot"}
    interest_attributes = {"frameStart", "frameEnd"}

    @classmethod
    def task_object_id(cls, session):
        if cls._cached_task_object_id is None:
            task_object_type = session.query(
                "ObjectType where name is \"Task\""
            ).one()
            cls._cached_task_object_id = task_object_type["id"]
        return cls._cached_task_object_id

    @classmethod
    def interest_object_ids(cls, session):
        if cls._cached_interest_object_ids is None:
            object_types = session.query(
                "ObjectType where name in ({})".format(
                    cls.join_query_keys(cls.interest_entity_types)
                )
            ).all()
            cls._cached_interest_object_ids = tuple(
                object_type["id"]
                for object_type in object_types
            )
        return cls._cached_interest_object_ids

    def session_user_id(self, session):
        if self._cached_user_id is None:
            user = session.query(
                "User where username is \"{}\"".format(session.api_user)
            ).one()
            self._cached_user_id = user["id"]
        return self._cached_user_id

    def launch(self, session, event):
        interesting_data, changed_keys_by_object_id = (
            self.extract_interesting_data(session, event)
        )
        if not interesting_data:
            return

        entities = self.get_entities(session, interesting_data)
        if not entities:
            return

        entities_by_id = {
            entity["id"]: entity
            for entity in entities
        }
        for entity_id in tuple(interesting_data.keys()):
            if entity_id not in entities_by_id:
                interesting_data.pop(entity_id)

        attrs_by_obj_id, hier_attrs = self.attrs_configurations(session)

        task_object_id = self.task_object_id(session)
        task_attrs = attrs_by_obj_id.get(task_object_id)
        # Skip keys that are not both in hierachical and type specific
        for object_id, keys in changed_keys_by_object_id.items():
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
                self.join_query_keys(self.interest_attributes),
                self.join_query_keys(self.interest_entity_types)
            ))
            return

        # Prepare task entities
        task_entities = []
        # If task entity does not contain changed attribute then skip
        if task_attrs:
            task_entities = self.get_task_entities(session, interesting_data)

        task_entities_by_id = {}
        parent_id_by_task_id = {}
        for task_entity in task_entities:
            task_entities_by_id[task_entity["id"]] = task_entity
            parent_id_by_task_id[task_entity["id"]] = task_entity["parent_id"]

        changed_keys = set()
        for keys in changed_keys_by_object_id.values():
            changed_keys |= set(keys)

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
            set(interesting_data.keys()) | set(task_entities_by_id.keys())
        )
        attr_ids = set(attr_id_to_key.keys())

        current_values_by_id = self.current_values(
            session, attr_ids, entity_ids, task_entities_by_id, hier_attrs
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

                entity_key = collections.OrderedDict({
                    "configuration_id": attr_id,
                    "entity_id": entity_id
                })
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

    def current_values(
        self, session, attr_ids, entity_ids, task_entities_by_id, hier_attrs
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
            if entity_id in task_entities_by_id and attr_id in hier_attrs:
                continue

            if entity_id not in current_values_by_id:
                current_values_by_id[entity_id] = {}
            current_values_by_id[entity_id][attr_id] = item["value"]
        return current_values_by_id

    def extract_interesting_data(self, session, event):
        # Filter if event contain relevant data
        entities_info = event["data"].get("entities")
        if not entities_info:
            return

        # for key, value in event["data"].items():
        #     self.log.info("{}: {}".format(key, value))
        session_user_id = self.session_user_id(session)
        user_data = event["data"].get("user")
        changed_by_session = False
        if user_data and user_data.get("userid") == session_user_id:
            changed_by_session = True

        current_time = datetime.datetime.now()

        interesting_data = {}
        changed_keys_by_object_id = {}
        for entity_info in entities_info:
            # Care only about tasks
            if entity_info.get("entityType") != "task":
                continue

            # Care only about changes of status
            changes = entity_info.get("changes") or {}
            if not changes:
                continue

            # Care only about changes if specific keys
            entity_changes = {}
            for key in self.interest_attributes:
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

            # Do not care about "Task" entity_type
            task_object_id = self.task_object_id(session)
            object_id = entity_info.get("objectTypeId")
            if not object_id or object_id == task_object_id:
                continue

            interesting_data[entity_id] = entity_changes
            if object_id not in changed_keys_by_object_id:
                changed_keys_by_object_id[object_id] = set()

            changed_keys_by_object_id[object_id] |= set(entity_changes.keys())

        return interesting_data, changed_keys_by_object_id

    def get_entities(self, session, interesting_data):
        entities = session.query(
            "TypedContext where id in ({})".format(
                self.join_query_keys(interesting_data.keys())
            )
        ).all()

        output = []
        interest_object_ids = self.interest_object_ids(session)
        for entity in entities:
            if entity["object_type_id"] in interest_object_ids:
                output.append(entity)
        return output

    def get_task_entities(self, session, interesting_data):
        return session.query(
            "Task where parent_id in ({})".format(
                self.join_query_keys(interesting_data.keys())
            )
        ).all()

    def attrs_configurations(self, session):
        object_ids = list(self.interest_object_ids(session))
        object_ids.append(self.task_object_id(session))

        attrs = session.query(self.cust_attrs_query.format(
            self.join_query_keys(self.interest_attributes),
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
