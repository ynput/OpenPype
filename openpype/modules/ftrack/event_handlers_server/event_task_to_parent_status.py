import collections
from openpype_modules.ftrack.lib import BaseEvent


class TaskStatusToParent(BaseEvent):
    settings_key = "status_task_to_parent"

    def launch(self, session, event):
        """Propagates status from task to parent when changed."""

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

        filtered_entity_info = collections.defaultdict(list)
        status_ids = set()
        for entity_info in entities_info:
            # Care only about tasks
            if entity_info.get("entityType") != "task":
                continue

            # Care only about changes of status
            changes = entity_info.get("changes")
            if not changes:
                continue
            statusid_changes = changes.get("statusid")
            if not statusid_changes:
                continue

            new_status_id = entity_info["changes"]["statusid"]["new"]
            if (
                statusid_changes.get("old") is None
                or new_status_id is None
            ):
                continue

            project_id = None
            for parent_item in reversed(entity_info["parents"]):
                if parent_item["entityType"] == "show":
                    project_id = parent_item["entityId"]
                    break

            if project_id:
                filtered_entity_info[project_id].append(entity_info)
                status_ids.add(new_status_id)

        return filtered_entity_info

    def process_by_project(self, session, event, project_id, entities_info):
        # Get project name
        project_name = self.get_project_name_from_event(
            session, event, project_id
        )
        # Load settings
        project_settings = self.get_project_settings_from_event(
            event, project_name
        )

        # Prepare loaded settings and check if can be processed
        result = self.prepare_settings(project_settings, project_name)
        if not result:
            return

        # Unpack the result
        parent_object_types, all_match, single_match = result

        # Prepare valid object type ids for object types from settings
        object_types = session.query("select id, name from ObjectType").all()
        object_type_id_by_low_name = {
            object_type["name"].lower(): object_type["id"]
            for object_type in object_types
        }

        valid_object_type_ids = set()
        for object_type_name in parent_object_types:
            if object_type_name in object_type_id_by_low_name:
                valid_object_type_ids.add(
                    object_type_id_by_low_name[object_type_name]
                )
            else:
                self.log.warning(
                    "Unknown object type \"{}\" set on project \"{}\".".format(
                        object_type_name, project_name
                    )
                )

        if not valid_object_type_ids:
            return

        # Prepare parent ids
        parent_ids = set()
        for entity_info in entities_info:
            parent_id = entity_info["parentId"]
            if parent_id:
                parent_ids.add(parent_id)

        # Query parent ids by object type ids and parent ids
        parent_entities = session.query(
            (
                "select id, status_id, object_type_id, link from TypedContext"
                " where id in ({}) and object_type_id in ({})"
            ).format(
                self.join_query_keys(parent_ids),
                self.join_query_keys(valid_object_type_ids)
            )
        ).all()
        # Skip if none of parents match the filtering
        if not parent_entities:
            return

        obj_ids = set()
        for entity in parent_entities:
            obj_ids.add(entity["object_type_id"])

        types_mapping = {
            _type.lower(): _type
            for _type in session.types
        }
        # Map object type id by lowered and modified object type name
        object_type_name_by_id = {}
        for object_type in object_types:
            mapping_name = object_type["name"].lower().replace(" ", "")
            obj_id = object_type["id"]
            object_type_name_by_id[obj_id] = types_mapping[mapping_name]

        project_entity = session.get("Project", project_id)
        project_schema = project_entity["project_schema"]
        available_statuses_by_obj_id = {}
        for obj_id in obj_ids:
            obj_name = object_type_name_by_id[obj_id]
            statuses = project_schema.get_statuses(obj_name)
            statuses_by_low_name = {
                status["name"].lower(): status
                for status in statuses
            }
            valid = False
            for name in all_match.keys():
                if name in statuses_by_low_name:
                    valid = True
                    break

            if not valid:
                for item in single_match:
                    if item["new_status"] in statuses_by_low_name:
                        valid = True
                        break
            if valid:
                available_statuses_by_obj_id[obj_id] = statuses_by_low_name

        valid_parent_ids = set()
        status_ids = set()
        valid_parent_entities = []
        for entity in parent_entities:
            if entity["object_type_id"] not in available_statuses_by_obj_id:
                continue

            valid_parent_entities.append(entity)
            valid_parent_ids.add(entity["id"])
            status_ids.add(entity["status_id"])

        if not valid_parent_ids:
            return

        task_entities = session.query(
            (
                "select id, parent_id, status_id from TypedContext"
                " where parent_id in ({}) and object_type_id is \"{}\""
            ).format(
                self.join_query_keys(valid_parent_ids),
                object_type_id_by_low_name["task"]
            )
        ).all()

        # This should not happen but it is safer
        if not task_entities:
            return

        task_entities_by_parent_id = collections.defaultdict(list)
        for task_entity in task_entities:
            status_ids.add(task_entity["status_id"])
            parent_id = task_entity["parent_id"]
            task_entities_by_parent_id[parent_id].append(task_entity)

        status_entities = session.query((
            "select id, name from Status where id in ({})"
        ).format(self.join_query_keys(status_ids))).all()

        statuses_by_id = {
            entity["id"]: entity
            for entity in status_entities
        }

        # New status determination logic
        new_statuses_by_parent_id = self.new_status_by_all_task_statuses(
            task_entities_by_parent_id, statuses_by_id, all_match
        )

        task_entities_by_id = {
            task_entity["id"]: task_entity
            for task_entity in task_entities
        }
        # Check if there are remaining any parents that does not have
        # determined new status yet
        remainder_tasks_by_parent_id = collections.defaultdict(list)
        for entity_info in entities_info:
            entity_id = entity_info["entityId"]
            if entity_id not in task_entities_by_id:
                continue
            parent_id = entity_info["parentId"]
            if (
                # Skip if already has determined new status
                parent_id in new_statuses_by_parent_id
                # Skip if parent is not in parent mapping
                # - if was not found or parent type is not interesting
                or parent_id not in task_entities_by_parent_id
            ):
                continue

            remainder_tasks_by_parent_id[parent_id].append(
                task_entities_by_id[entity_id]
            )

        # Try to find new status for remained parents
        new_statuses_by_parent_id.update(
            self.new_status_by_remainders(
                remainder_tasks_by_parent_id,
                statuses_by_id,
                single_match
            )
        )

        # If there are not new statuses then just skip
        if not new_statuses_by_parent_id:
            return

        parent_entities_by_id = {
            parent_entity["id"]: parent_entity
            for parent_entity in valid_parent_entities
        }
        for parent_id, new_status_name in new_statuses_by_parent_id.items():
            if not new_status_name:
                continue

            parent_entity = parent_entities_by_id[parent_id]
            ent_path = "/".join(
                [ent["name"] for ent in parent_entity["link"]]
            )

            obj_id = parent_entity["object_type_id"]
            statuses_by_low_name = available_statuses_by_obj_id.get(obj_id)
            if not statuses_by_low_name:
                continue

            new_status = statuses_by_low_name.get(new_status_name)
            if not new_status:
                self.log.warning((
                    "\"{}\" Couldn't change status to \"{}\"."
                    " Status is not available for entity type \"{}\"."
                ).format(
                    ent_path, new_status_name, parent_entity.entity_type
                ))
                continue

            current_status = parent_entity["status"]
            # Do nothing if status is already set
            if new_status["id"] == current_status["id"]:
                self.log.debug(
                    "\"{}\" Status \"{}\" already set.".format(
                        ent_path, current_status["name"]
                    )
                )
                continue

            try:
                parent_entity["status_id"] = new_status["id"]
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

    def prepare_settings(self, project_settings, project_name):
        event_settings = (
            project_settings["ftrack"]["events"][self.settings_key]
        )

        if not event_settings["enabled"]:
            self.log.debug("Project \"{}\" has disabled {}.".format(
                project_name, self.__class__.__name__
            ))
            return

        _parent_object_types = event_settings["parent_object_types"]
        if not _parent_object_types:
            self.log.debug((
                "Project \"{}\" does not have set"
                " parent object types filtering."
            ).format(project_name))
            return

        _all_match = (
            event_settings["parent_status_match_all_task_statuses"]
        )
        _single_match = (
            event_settings["parent_status_by_task_status"]
        )

        if not _all_match and not _single_match:
            self.log.debug((
                "Project \"{}\" does not have set"
                " parent status mappings."
            ).format(project_name))
            return

        parent_object_types = [
            item.lower()
            for item in _parent_object_types
        ]
        all_match = {}
        for new_status_name, task_statuses in _all_match.items():
            all_match[new_status_name.lower()] = [
                status_name.lower()
                for status_name in task_statuses
            ]

        single_match = []
        for item in _single_match:
            single_match.append({
                "new_status": item["new_status"].lower(),
                "task_statuses": [
                    status_name.lower()
                    for status_name in item["task_statuses"]
                ]
            })
        return parent_object_types, all_match, single_match

    def new_status_by_all_task_statuses(
        self, tasks_by_parent_id, statuses_by_id, all_match
    ):
        """All statuses of parent entity must match specific status names.

        Only if all task statuses match the condition parent's status name is
        determined.
        """
        output = {}
        for parent_id, task_entities in tasks_by_parent_id.items():
            task_statuses_lowered = set()
            for task_entity in task_entities:
                task_status = statuses_by_id[task_entity["status_id"]]
                low_status_name = task_status["name"].lower()
                task_statuses_lowered.add(low_status_name)

            new_status = None
            for _new_status, task_statuses in all_match.items():
                valid_item = True
                for status_name_low in task_statuses_lowered:
                    if status_name_low not in task_statuses:
                        valid_item = False
                        break

                if valid_item:
                    new_status = _new_status
                    break

            if new_status is not None:
                output[parent_id] = new_status

        return output

    def new_status_by_remainders(
        self, remainder_tasks_by_parent_id, statuses_by_id, single_match
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
            #   list `single_match` is preffered
            best_order = len(single_match)
            best_order_status = None
            for task_entity in task_entities:
                task_status = statuses_by_id[task_entity["status_id"]]
                low_status_name = task_status["name"].lower()
                for order, item in enumerate(single_match):
                    if order >= best_order:
                        break

                    if low_status_name in item["task_statuses"]:
                        best_order = order
                        best_order_status = item["new_status"]
                        break

            if best_order_status:
                output[parent_id] = best_order_status
        return output


def register(session):
    TaskStatusToParent(session).register()
