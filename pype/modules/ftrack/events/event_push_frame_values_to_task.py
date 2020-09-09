import collections
import ftrack_api
from pype.modules.ftrack import BaseEvent


class PushFrameValuesToTaskEvent(BaseEvent):
    # Ignore event handler by default
    ignore_me = True

    cust_attrs_query = (
        "select id, key, object_type_id, is_hierarchical, default"
        " from CustomAttributeConfiguration"
        " where key in ({}) and object_type_id in ({})"
    )

    interest_entity_types = {"Shot"}
    interest_attributes = {"frameStart", "frameEnd"}
    interest_attr_mapping = {
        "frameStart": "fstart",
        "frameEnd": "fend"
    }
    _cached_task_object_id = None
    _cached_interest_object_ids = None

    @staticmethod
    def join_keys(keys):
        return ",".join(["\"{}\"".format(key) for key in keys])

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
                    cls.join_keys(cls.interest_entity_types)
                )
            ).all()
            cls._cached_interest_object_ids = tuple(
                object_type["id"]
                for object_type in object_types
            )
        return cls._cached_interest_object_ids

    def launch(self, session, event):
        interesting_data = self.extract_interesting_data(session, event)
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

        task_entities = self.get_task_entities(session, interesting_data)

        attrs_by_obj_id = self.attrs_configurations(session)
        if not attrs_by_obj_id:
            self.log.warning((
                "There is not created Custom Attributes {}"
                " for \"Task\" entity type."
            ).format(self.join_keys(self.interest_attributes)))
            return

        task_entities_by_parent_id = collections.defaultdict(list)
        for task_entity in task_entities:
            task_entities_by_parent_id[task_entity["parent_id"]].append(
                task_entity
            )

        missing_keys_by_object_name = collections.defaultdict(set)
        for parent_id, values in interesting_data.items():
            entities = task_entities_by_parent_id.get(parent_id) or []
            entities.append(entities_by_id[parent_id])

            for hier_key, value in values.items():
                changed_ids = []
                for entity in entities:
                    key = self.interest_attr_mapping[hier_key]
                    entity_attrs_mapping = (
                        attrs_by_obj_id.get(entity["object_type_id"])
                    )
                    if not entity_attrs_mapping:
                        missing_keys_by_object_name[entity.entity_type].add(
                            key
                        )
                        continue

                    configuration_id = entity_attrs_mapping.get(key)
                    if not configuration_id:
                        missing_keys_by_object_name[entity.entity_type].add(
                            key
                        )
                        continue

                    changed_ids.append(entity["id"])
                    entity_key = collections.OrderedDict({
                        "configuration_id": configuration_id,
                        "entity_id": entity["id"]
                    })
                    if value is None:
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
                            value
                        )

                    session.recorded_operations.push(op)
                self.log.info((
                    "Changing Custom Attribute \"{}\" to value"
                    " \"{}\" on entities: {}"
                ).format(key, value, self.join_keys(changed_ids)))
                try:
                    session.commit()
                except Exception:
                    session.rollback()
                    self.log.warning(
                        "Changing of values failed.",
                        exc_info=True
                    )
        if not missing_keys_by_object_name:
            return

        msg_items = []
        for object_name, missing_keys in missing_keys_by_object_name.items():
            msg_items.append(
                "{}: ({})".format(object_name, self.join_keys(missing_keys))
            )

        self.log.warning((
            "Missing Custom Attribute configuration"
            " per specific object types: {}"
        ).format(", ".join(msg_items)))

    def extract_interesting_data(self, session, event):
        # Filter if event contain relevant data
        entities_info = event["data"].get("entities")
        if not entities_info:
            return

        interesting_data = {}
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

            if not entity_changes:
                continue

            # Do not care about "Task" entity_type
            task_object_id = self.task_object_id(session)
            if entity_info.get("objectTypeId") == task_object_id:
                continue

            interesting_data[entity_info["entityId"]] = entity_changes
        return interesting_data

    def get_entities(self, session, interesting_data):
        entities = session.query(
            "TypedContext where id in ({})".format(
                self.join_keys(interesting_data.keys())
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
                self.join_keys(interesting_data.keys())
            )
        ).all()

    def attrs_configurations(self, session):
        object_ids = list(self.interest_object_ids(session))
        object_ids.append(self.task_object_id(session))

        attrs = session.query(self.cust_attrs_query.format(
            self.join_keys(self.interest_attr_mapping.values()),
            self.join_keys(object_ids)
        )).all()

        output = {}
        for attr in attrs:
            obj_id = attr["object_type_id"]
            if obj_id not in output:
                output[obj_id] = {}
            output[obj_id][attr["key"]] = attr["id"]
        return output


def register(session, plugins_presets):
    PushFrameValuesToTaskEvent(session, plugins_presets).register()
