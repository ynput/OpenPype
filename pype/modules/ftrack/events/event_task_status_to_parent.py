import collections
from pype.modules.ftrack import BaseEvent


class TaskStatusToParent(BaseEvent):
    # Parent types where we care about changing of status
    parent_types = ["shot", "asset build"]

    # All parent's tasks must have status name in `task_statuses` key to apply
    # status name in `new_status`
    parent_status_match_all_task_statuses = [
        {
            "new_status": "approved",
            "task_statuses": [
                "approved", "omitted"
            ]
        }
    ]

    # Task's status was changed to something in `task_statuses` to apply
    # `new_status` on it's parent
    # - this is done only if `parent_status_match_all_task_statuses` filtering
    #   didn't found matching status
    parent_status_match_task_statuse = [
        {
            "new_status": "in progress",
            "task_statuses": [
                "in progress"
            ]
        }
    ]

    def register(self, *args, **kwargs):
        result = super(TaskStatusToParent, self).register(*args, **kwargs)
        # Clean up presetable attributes
        _new_all_match = []
        if self.parent_status_match_all_task_statuses:
            for item in self.parent_status_match_all_task_statuses:
                _new_all_match.append({
                    "new_status": item["new_status"].lower(),
                    "task_statuses": [
                        status_name.lower()
                        for status_name in item["task_statuses"]
                    ]
                })
        self.parent_status_match_all_task_statuses = _new_all_match

        _new_single_match = []
        if self.parent_status_match_task_statuse:
            for item in self.parent_status_match_task_statuse:
                _new_single_match.append({
                    "new_status": item["new_status"].lower(),
                    "task_statuses": [
                        status_name.lower()
                        for status_name in item["task_statuses"]
                    ]
                })
        self.parent_status_match_task_statuse = _new_single_match

        self.parent_types = [
            parent_type.lower()
            for parent_type in self.parent_types
        ]

        return result

    def filter_entities_info(self, session, event):
        # Filter if event contain relevant data
        entities_info = event["data"].get("entities")
        if not entities_info:
            return

        filtered_entities = []
        for entity_info in entities_info:
            # Care only about tasks
            if entity_info.get("entityType") != "task":
                continue

            # Care only about changes of status
            changes = entity_info.get("changes") or {}
            statusid_changes = changes.get("statusid") or {}
            if (
                statusid_changes.get("new") is None
                or statusid_changes.get("old") is None
            ):
                continue

            filtered_entities.append(entity_info)

        status_ids = [
            entity_info["changes"]["statusid"]["new"]
            for entity_info in filtered_entities
        ]
        statuses_by_id = self.get_statuses_by_id(
            session, status_ids=status_ids
        )

        # Care only about tasks having status with state `Done`
        output = []
        for entity_info in filtered_entities:
            status_id = entity_info["changes"]["statusid"]["new"]
            entity_info["status_entity"] = statuses_by_id[status_id]
            output.append(entity_info)
        return output

    def get_parents_by_id(self, session, entities_info, object_types):
        task_type_id = None
        valid_object_type_ids = []
        for object_type in object_types:
            object_name_low = object_type["name"].lower()
            if object_name_low == "task":
                task_type_id = object_type["id"]

            if object_name_low in self.parent_types:
                valid_object_type_ids.append(object_type["id"])

        parent_ids = [
            "\"{}\"".format(entity_info["parentId"])
            for entity_info in entities_info
            if entity_info["objectTypeId"] == task_type_id
        ]
        if not parent_ids:
            return {}

        parent_entities = session.query((
            "TypedContext where id in ({}) and object_type_id in ({})"
        ).format(
            ", ".join(parent_ids), ", ".join(valid_object_type_ids))
        ).all()

        return {
            entity["id"]: entity
            for entity in parent_entities
        }

    def get_tasks_by_id(self, session, parent_ids):
        joined_parent_ids = ",".join([
            "\"{}\"".format(parent_id)
            for parent_id in parent_ids
        ])
        task_entities = session.query(
            "Task where parent_id in ({})".format(joined_parent_ids)
        ).all()

        return {
            entity["id"]: entity
            for entity in task_entities
        }

    def get_statuses_by_id(self, session, task_entities=None, status_ids=None):
        if task_entities is None and status_ids is None:
            return {}

        if status_ids is None:
            status_ids = []
            for task_entity in task_entities:
                status_ids.append(task_entity["status_id"])

        if not status_ids:
            return {}

        status_entities = session.query(
            "Status where id in ({})".format(", ".join(status_ids))
        ).all()

        return {
            entity["id"]: entity
            for entity in status_entities
        }

    def launch(self, session, event):
        '''Propagates status from version to task when changed'''

        entities_info = self.filter_entities_info(session, event)
        if not entities_info:
            return

        object_types = session.query("select id, name from ObjectType").all()
        parents_by_id = self.get_parents_by_id(
            session, entities_info, object_types
        )
        if not parents_by_id:
            return
        tasks_by_id = self.get_tasks_by_id(
            session, tuple(parents_by_id.keys())
        )

        # Just collect them in one variable
        entities_by_id = {}
        for entity_id, entity in parents_by_id.items():
            entities_by_id[entity_id] = entity
        for entity_id, entity in tasks_by_id.items():
            entities_by_id[entity_id] = entity

        # Map task entities by their parents
        tasks_by_parent_id = collections.defaultdict(list)
        for task_entity in tasks_by_id.values():
            tasks_by_parent_id[task_entity["parent_id"]].append(task_entity)

        # Found status entities for all queried entities
        statuses_by_id = self.get_statuses_by_id(
            session,
            entities_by_id.values()
        )

        # New status determination logic
        new_statuses_by_parent_id = self.new_status_by_all_task_statuses(
            parents_by_id.keys(), tasks_by_parent_id, statuses_by_id
        )

        # Check if there are remaining any parents that does not have
        # determined new status yet
        remainder_tasks_by_parent_id = collections.defaultdict(list)
        for entity_info in entities_info:
            parent_id = entity_info["parentId"]
            if (
                # Skip if already has determined new status
                parent_id in new_statuses_by_parent_id
                # Skip if parent is not in parent mapping
                # - if was not found or parent type is not interesting
                or parent_id not in parents_by_id
            ):
                continue

            remainder_tasks_by_parent_id[parent_id].append(
                entities_by_id[entity_info["entityId"]]
            )

        # Try to find new status for remained parents
        new_statuses_by_parent_id.update(
            self.new_status_by_remainders(
                remainder_tasks_by_parent_id,
                statuses_by_id
            )
        )

        # Make sure new_status is set to valid value
        for parent_id in tuple(new_statuses_by_parent_id.keys()):
            new_status_name = new_statuses_by_parent_id[parent_id]
            if not new_status_name:
                new_statuses_by_parent_id.pop(parent_id)

        # If there are not new statuses then just skip
        if not new_statuses_by_parent_id:
            return

        # Get project schema from any available entity
        _entity = None
        for _ent in entities_by_id.values():
            _entity = _ent
            break

        project_entity = self.get_project_from_entity(_entity)
        project_schema = project_entity["project_schema"]

        # Map type names by lowere type names
        types_mapping = {
            _type.lower(): _type
            for _type in session.types
        }
        # Map object type id by lowered and modified object type name
        object_type_mapping = {}
        for object_type in object_types:
            mapping_name = object_type["name"].lower().replace(" ", "")
            object_type_mapping[object_type["id"]] = mapping_name

        statuses_by_obj_id = {}
        for parent_id, new_status_name in new_statuses_by_parent_id.items():
            if not new_status_name:
                continue
            parent_entity = entities_by_id[parent_id]
            obj_id = parent_entity["object_type_id"]

            # Find statuses for entity type by object type name
            # in project's schema and cache them
            if obj_id not in statuses_by_obj_id:
                mapping_name = object_type_mapping[obj_id]
                mapped_name = types_mapping.get(mapping_name)
                statuses = project_schema.get_statuses(mapped_name)
                statuses_by_obj_id[obj_id] = {
                    status["name"].lower(): status
                    for status in statuses
                }

            statuses_by_name = statuses_by_obj_id[obj_id]
            new_status = statuses_by_name.get(new_status_name)
            ent_path = "/".join(
                [ent["name"] for ent in parent_entity["link"]]
            )
            if not new_status:
                self.log.warning((
                    "\"{}\" Couldn't change status to \"{}\"."
                    " Status is not available for entity type \"{}\"."
                ).format(
                    new_status_name, ent_path, parent_entity.entity_type
                ))
                continue

            # Do nothing if status is already set
            if new_status["name"].lower() == new_status_name:
                continue

            try:
                parent_entity["status"] = new_status
                session.commit()
                self.log.info(
                    "\"{}\" changed status to \"{}\"".format(
                        ent_path, new_status["name"]
                    )
                )
            except Exception:
                session.rollback()
                self.log.warning(
                    "\"{}\" status couldnt be set to \"{}\"".format(
                        ent_path, new_status["name"]
                    ),
                    exc_info=True
                )

    def new_status_by_all_task_statuses(
        self, parent_ids, tasks_by_parent_id, statuses_by_id
    ):
        """All statuses of parent entity must match specific status names.

        Only if all task statuses match the condition parent's status name is
        determined.
        """
        output = {}
        for parent_id in parent_ids:
            task_statuses_lowered = set()
            for task_entity in tasks_by_parent_id[parent_id]:
                task_status = statuses_by_id[task_entity["status_id"]]
                low_status_name = task_status["name"].lower()
                task_statuses_lowered.add(low_status_name)

            new_status = None
            for item in self.parent_status_match_all_task_statuses:
                valid_item = True
                for status_name_low in task_statuses_lowered:
                    if status_name_low not in item["task_statuses"]:
                        valid_item = False
                        break

                if valid_item:
                    new_status = item["new_status"]
                    break

            if new_status is not None:
                output[parent_id] = new_status

        return output

    def new_status_by_remainders(
        self, remainder_tasks_by_parent_id, statuses_by_id
    ):
        """By new task status can be determined new status of parent."""
        output = {}
        if not remainder_tasks_by_parent_id:
            return output

        for parent_id, task_entities in remainder_tasks_by_parent_id.items():
            if not task_entities:
                continue

            # For cases there are multiple tasks in changes
            # - task status which match any new status item by order in the
            #   list `parent_status_match_task_statuse` is preffered
            best_order = len(self.parent_status_match_task_statuse)
            best_order_status = None
            for task_entity in task_entities:
                task_status = statuses_by_id[task_entity["status_id"]]
                low_status_name = task_status["name"].lower()
                for order, item in enumerate(
                    self.parent_status_match_task_statuse
                ):
                    if order >= best_order:
                        break

                    if low_status_name in item["task_statuses"]:
                        best_order = order
                        best_order_status = item["new_status"]
                        break

            if best_order_status:
                output[parent_id] = best_order_status
        return output


def register(session, plugins_presets):
    TaskStatusToParent(session, plugins_presets).register()
