import collections
import ftrack_api
from pype.modules.ftrack import BaseEvent


class PushFrameValuesToTaskEvent(BaseEvent):
    """Action for testing purpose or as base for new actions."""
    cust_attrs_query = (
        "select id, key, object_type_id, is_hierarchical, default"
        " from CustomAttributeConfiguration"
        " where key in ({}) and object_type_id = {}"
    )

    # Ignore event handler by default
    ignore_me = True

    interest_attributes = ["frameStart", "frameEnd"]
    _cached_task_object_id = None

    @classmethod
    def task_object_id(cls, session):
        if cls._cached_task_object_id is None:
            task_object_type = session.query(
                "ObjectType where name is \"Task\""
            ).one()
            cls._cached_task_object_id = task_object_type["id"]
        return cls._cached_task_object_id

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

    def join_keys(self, keys):
        return ",".join(["\"{}\"".format(key) for key in keys])

    def get_task_entities(self, session, entities_info):
        return session.query(
            "Task where parent_id in ({})".format(
                self.join_keys(entities_info.keys())
            )
        ).all()

    def task_attrs(self, session):
        return session.query(self.cust_attrs_query.format(
            self.join_keys(self.interest_attributes),
            self.task_object_id(session)
        )).all()

    def launch(self, session, event):
        interesting_data = self.extract_interesting_data(session, event)
        if not interesting_data:
            return

        task_entities = self.get_task_entities(session, interesting_data)
        if not task_entities:
            return

        task_attrs = self.task_attrs(session)
        if not task_attrs:
            self.log.warning((
                "There is not created Custom Attributes {}"
                " for \"Task\" entity type."
            ).format(self.join_keys(self.interest_attributes)))
            return

        task_attr_id_by_key = {
            attr["key"]: attr["id"]
            for attr in task_attrs
        }
        task_entities_by_parent_id = collections.defaultdict(list)
        for task_entity in task_entities:
            task_entities_by_parent_id[task_entity["parent_id"]].append(
                task_entity
            )

        for parent_id, values in interesting_data.items():
            task_entities = task_entities_by_parent_id[parent_id]
            for key, value in values.items():
                changed_ids = []
                for task_entity in task_entities:
                    task_id = task_entity["id"]
                    changed_ids.append(task_id)

                    entity_key = collections.OrderedDict({
                        "configuration_id": task_attr_id_by_key[key],
                        "entity_id": task_id
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


def register(session, plugins_presets):
    PushFrameValuesToTaskEvent(session, plugins_presets).register()
