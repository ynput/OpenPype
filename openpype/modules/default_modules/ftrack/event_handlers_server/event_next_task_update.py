import collections
from openpype_modules.ftrack.lib import BaseEvent


class NextTaskUpdate(BaseEvent):
    """Change status on following Task.

    Handler cares about changes of status id on Task entities. When new status
    has state "Done" it will try to find following task and change it's status.
    It is expected following task should be marked as "Ready to work on".

    By default all tasks with same task type must have state "Done" to do any
    changes. And when all tasks with same task type are "done" it will change
    statuses on all tasks with next task type.

    # Enable
    Handler is based on settings, handler can be turned on/off with "enabled"
    key.
    ```
    "enabled": True
    ```

    # Status mappings
    Must have set mappings of new statuses:
    ```
    "mapping": {
        # From -> To
        "Not Ready": "Ready",
        ...
    }
    ```

    If current status name is not found then status change is skipped.

    # Ignored statuses
    These status names are skipping as they would be in "Done" state. Best
    example is status "Omitted" which in most of cases is "Blocked" state but
    it will never change.
    ```
    "ignored_statuses": [
        "Omitted",
        ...
    ]
    ```

    # Change statuses sorted by task type and by name
    Change behaviour of task type batching. Statuses are not checked and set
    by batches of tasks by Task type but one by one. Tasks are sorted by
    Task type and then by name if all previous tasks are "Done" the following
    will change status.
    ```
    "name_sorting": True
    ```
    """
    settings_key = "next_task_update"

    def launch(self, session, event):
        '''Propagates status from version to task when changed'''

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

        filtered_entities_info = collections.defaultdict(list)
        for entity_info in entities_info:
            # Care only about Task `entity_type`
            if entity_info.get("entity_type") != "Task":
                continue

            # Care only about changes of status
            changes = entity_info.get("changes") or {}
            statusid_changes = changes.get("statusid") or {}
            if (
                statusid_changes.get("new") is None
                or statusid_changes.get("old") is None
            ):
                continue

            project_id = None
            for parent_info in reversed(entity_info["parents"]):
                if parent_info["entityType"] == "show":
                    project_id = parent_info["entityId"]
                    break

            if project_id:
                filtered_entities_info[project_id].append(entity_info)
        return filtered_entities_info

    def process_by_project(self, session, event, project_id, _entities_info):
        project_name = self.get_project_name_from_event(
            session, event, project_id
        )
        # Load settings
        project_settings = self.get_project_settings_from_event(
            event, project_name
        )

        # Load status mapping from presets
        event_settings = (
            project_settings["ftrack"]["events"][self.settings_key]
        )
        if not event_settings["enabled"]:
            self.log.debug("Project \"{}\" has disabled {}.".format(
                project_name, self.__class__.__name__
            ))
            return

        statuses = session.query("Status").all()

        entities_info = self.filter_by_status_state(_entities_info, statuses)
        if not entities_info:
            return

        parent_ids = set()
        event_task_ids_by_parent_id = collections.defaultdict(list)
        for entity_info in entities_info:
            parent_id = entity_info["parentId"]
            entity_id = entity_info["entityId"]
            parent_ids.add(parent_id)
            event_task_ids_by_parent_id[parent_id].append(entity_id)

        # From now it doesn't matter what was in event data
        task_entities = session.query(
            (
                "select id, type_id, status_id, parent_id, link from Task"
                " where parent_id in ({})"
            ).format(self.join_query_keys(parent_ids))
        ).all()

        tasks_by_parent_id = collections.defaultdict(list)
        for task_entity in task_entities:
            tasks_by_parent_id[task_entity["parent_id"]].append(task_entity)

        project_entity = session.get("Project", project_id)
        self.set_next_task_statuses(
            session,
            tasks_by_parent_id,
            event_task_ids_by_parent_id,
            statuses,
            project_entity,
            event_settings
        )

    def filter_by_status_state(self, entities_info, statuses):
        statuses_by_id = {
            status["id"]: status
            for status in statuses
        }

        # Care only about tasks having status with state `Done`
        filtered_entities_info = []
        for entity_info in entities_info:
            status_id = entity_info["changes"]["statusid"]["new"]
            status_entity = statuses_by_id[status_id]
            if status_entity["state"]["name"].lower() == "done":
                filtered_entities_info.append(entity_info)
        return filtered_entities_info

    def set_next_task_statuses(
        self,
        session,
        tasks_by_parent_id,
        event_task_ids_by_parent_id,
        statuses,
        project_entity,
        event_settings
    ):
        statuses_by_id = {
            status["id"]: status
            for status in statuses
        }

        # Lower ignored statuses
        ignored_statuses = set(
            status_name.lower()
            for status_name in event_settings["ignored_statuses"]
        )
        # Lower both key and value of mapped statuses
        mapping = {
            status_from.lower(): status_to.lower()
            for status_from, status_to in event_settings["mapping"].items()
        }
        # Should use name sorting or not
        name_sorting = event_settings["name_sorting"]

        # Collect task type ids from changed entities
        task_type_ids = set()
        for task_entities in tasks_by_parent_id.values():
            for task_entity in task_entities:
                task_type_ids.add(task_entity["type_id"])

        statusese_by_obj_id = self.statuses_for_tasks(
            task_type_ids, project_entity
        )

        sorted_task_type_ids = self.get_sorted_task_type_ids(session)

        for parent_id, _task_entities in tasks_by_parent_id.items():
            task_entities_by_type_id = collections.defaultdict(list)
            for _task_entity in _task_entities:
                type_id = _task_entity["type_id"]
                task_entities_by_type_id[type_id].append(_task_entity)

            event_ids = set(event_task_ids_by_parent_id[parent_id])
            if name_sorting:
                # Sort entities by name
                self.sort_by_name_task_entities_by_type(
                    task_entities_by_type_id
                )
                # Sort entities by type id
                sorted_task_entities = []
                for type_id in sorted_task_type_ids:
                    task_entities = task_entities_by_type_id.get(type_id)
                    if task_entities:
                        sorted_task_entities.extend(task_entities)

                next_tasks = self.next_tasks_with_name_sorting(
                    sorted_task_entities,
                    event_ids,
                    statuses_by_id,
                    ignored_statuses
                )

            else:
                next_tasks = self.next_tasks_with_type_sorting(
                    task_entities_by_type_id,
                    sorted_task_type_ids,
                    event_ids,
                    statuses_by_id,
                    ignored_statuses
                )

        for task_entity in next_tasks:
            if task_entity["status"]["state"]["name"].lower() == "done":
                continue

            task_status = statuses_by_id[task_entity["status_id"]]
            old_status_name = task_status["name"].lower()
            if old_status_name in ignored_statuses:
                continue

            new_task_name = mapping.get(old_status_name)
            if not new_task_name:
                self.log.debug(
                    "Didn't found mapping for status \"{}\".".format(
                        task_status["name"]
                    )
                )
                continue

            ent_path = "/".join(
                [ent["name"] for ent in task_entity["link"]]
            )
            type_id = task_entity["type_id"]
            new_status = statusese_by_obj_id[type_id].get(new_task_name)
            if new_status is None:
                self.log.warning((
                    "\"{}\" does not have available status name \"{}\""
                ).format(ent_path, new_task_name))
                continue

            try:
                task_entity["status_id"] = new_status["id"]
                session.commit()
                self.log.info(
                    "\"{}\" updated status to \"{}\"".format(
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

    def next_tasks_with_name_sorting(
        self,
        sorted_task_entities,
        event_ids,
        statuses_by_id,
        ignored_statuses,
    ):
        # Pre sort task entities by name
        use_next_task = False
        next_tasks = []
        for task_entity in sorted_task_entities:
            if task_entity["id"] in event_ids:
                event_ids.remove(task_entity["id"])
                use_next_task = True
                continue

            if not use_next_task:
                continue

            task_status = statuses_by_id[task_entity["status_id"]]
            low_status_name = task_status["name"].lower()
            if low_status_name in ignored_statuses:
                continue

            next_tasks.append(task_entity)
            use_next_task = False
            if not event_ids:
                break

        return next_tasks

    def check_statuses_done(
        self, task_entities, ignored_statuses, statuses_by_id
    ):
        all_are_done = True
        for task_entity in task_entities:
            task_status = statuses_by_id[task_entity["status_id"]]
            low_status_name = task_status["name"].lower()
            if low_status_name in ignored_statuses:
                continue

            low_state_name = task_status["state"]["name"].lower()
            if low_state_name != "done":
                all_are_done = False
                break
        return all_are_done

    def next_tasks_with_type_sorting(
        self,
        task_entities_by_type_id,
        sorted_task_type_ids,
        event_ids,
        statuses_by_id,
        ignored_statuses
    ):
        # `use_next_task` is used only if `name_sorting` is enabled!
        next_tasks = []
        use_next_tasks = False
        for type_id in sorted_task_type_ids:
            if type_id not in task_entities_by_type_id:
                continue

            task_entities = task_entities_by_type_id[type_id]

            # Check if any task was in event
            event_id_in_tasks = False
            for task_entity in task_entities:
                task_id = task_entity["id"]
                if task_id in event_ids:
                    event_ids.remove(task_id)
                    event_id_in_tasks = True

            if use_next_tasks:
                # Check if next tasks are not done already
                all_in_type_done = self.check_statuses_done(
                    task_entities, ignored_statuses, statuses_by_id
                )
                if all_in_type_done:
                    continue

                next_tasks.extend(task_entities)
                use_next_tasks = False
                if not event_ids:
                    break

            if not event_id_in_tasks:
                continue

            all_in_type_done = self.check_statuses_done(
                task_entities, ignored_statuses, statuses_by_id
            )
            use_next_tasks = all_in_type_done
            if all_in_type_done:
                continue

            if not event_ids:
                break

            use_next_tasks = False

        return next_tasks

    def statuses_for_tasks(self, task_type_ids, project_entity):
        project_schema = project_entity["project_schema"]
        output = {}
        for task_type_id in task_type_ids:
            statuses = project_schema.get_statuses("Task", task_type_id)
            output[task_type_id] = {
                status["name"].lower(): status
                for status in statuses
            }

        return output

    def get_sorted_task_type_ids(self, session):
        types_by_order = collections.defaultdict(list)
        for _type in session.query("Type").all():
            sort_oder = _type.get("sort")
            if sort_oder is not None:
                types_by_order[sort_oder].append(_type["id"])

        types = []
        for sort_oder in sorted(types_by_order.keys()):
            types.extend(types_by_order[sort_oder])
        return types

    @staticmethod
    def sort_by_name_task_entities_by_type(task_entities_by_type_id):
        _task_entities_by_type_id = {}
        for type_id, task_entities in task_entities_by_type_id.items():
            # Store tasks by name
            task_entities_by_name = {}
            for task_entity in task_entities:
                task_name = task_entity["name"]
                task_entities_by_name[task_name] = task_entity

            # Store task entities by sorted names
            sorted_task_entities = []
            for task_name in sorted(task_entities_by_name.keys()):
                task_entity = task_entities_by_name[task_name]
                sorted_task_entities.append(task_entity)
            # Store result to temp dictionary
            _task_entities_by_type_id[type_id] = sorted_task_entities

        # Override values in source object
        for type_id, value in _task_entities_by_type_id.items():
            task_entities_by_type_id[type_id] = value


def register(session):
    NextTaskUpdate(session).register()
