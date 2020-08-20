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
        "select id, name, parent_id, link"
        " from TypedContext where project_id is \"{}\""
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
    custom_attribute_keys = {"frameStart", "frameEnd"}
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
        # TODO this can be threaded
        task_attrs_by_key, hier_attrs = self.frame_attributes(session)
        missing_keys = [
            key
            for key in self.custom_attribute_keys
            if key not in task_attrs_by_key
        ]
        if missing_keys:
            if len(missing_keys) == 1:
                sub_msg = " \"{}\"".format(missing_keys[0])
            else:
                sub_msg = "s {}".format(", ".join([
                    "\"{}\"".format(key)
                    for key in missing_keys
                ]))

            msg = "Missing Task's custom attribute{}.".format(sub_msg)
            self.log.warning(msg)
            return {
                "success": False,
                "message": msg
            }

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
            result = self.propagate_values(
                session,
                tuple(task_attrs_by_key.values()),
                hier_attrs,
                project_entity
            )
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

    def frame_attributes(self, session):
        task_object_type = session.query(
            "ObjectType where name is \"Task\""
        ).one()

        joined_keys = self.join_keys(self.custom_attribute_keys)
        attribute_entities = session.query(
            self.cust_attrs_query.format(joined_keys)
        ).all()

        hier_attrs = []
        task_attrs = {}
        for attr in attribute_entities:
            attr_key = attr["key"]
            if attr["is_hierarchical"]:
                hier_attrs.append(attr)
            elif attr["object_type_id"] == task_object_type["id"]:
                task_attrs[attr_key] = attr
        return task_attrs, hier_attrs

    def join_keys(self, items):
        return ",".join(["\"{}\"".format(item) for item in items])

    def propagate_values(
        self, session, task_attrs, hier_attrs, project_entity
    ):
        self.log.debug("Querying project's entities \"{}\".".format(
            project_entity["full_name"]
        ))
        entities = session.query(
            self.entities_query.format(project_entity["id"])
        ).all()

        self.log.debug("Filtering Task entities.")
        task_entities_by_parent_id = collections.defaultdict(list)
        for entity in entities:
            if entity.entity_type.lower() == "task":
                task_entities_by_parent_id[entity["parent_id"]].append(entity)

        self.log.debug("Getting Custom attribute values from tasks' parents.")
        hier_values_by_entity_id = self.get_hier_values(
            session,
            hier_attrs,
            list(task_entities_by_parent_id.keys())
        )

        self.log.debug("Setting parents' values to task.")
        self.set_task_attr_values(
            session,
            task_entities_by_parent_id,
            hier_values_by_entity_id,
            task_attrs
        )

        return True

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
        task_attrs
    ):
        task_attr_ids_by_key = {
            attr["key"]: attr["id"]
            for attr in task_attrs
        }

        total_parents = len(hier_values_by_entity_id)
        idx = 1
        for parent_id, values in hier_values_by_entity_id.items():
            self.log.info((
                "[{}/{}] {} Processing values to children. Values: {}"
            ).format(idx, total_parents, parent_id, values))
            idx += 1

            task_entities = task_entities_by_parent_id[parent_id]
            for key, value in values.items():
                for task_entity in task_entities:
                    _entity_key = collections.OrderedDict({
                        "configuration_id": task_attr_ids_by_key[key],
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


def register(session, plugins_presets={}):
    PushFrameValuesToTaskAction(session, plugins_presets).register()
