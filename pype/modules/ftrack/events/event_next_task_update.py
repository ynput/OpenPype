import collections
from pype.modules.ftrack import BaseEvent


class NextTaskUpdate(BaseEvent):
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

        filtered_entities_info = {}
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
        project_entity = self.get_project_entity_from_event(
            session, event, project_id
        )
        project_settings = self.get_settings_for_project(
            session, event, project_entity=project_entity
        )

        project_name = project_entity["full_name"]

        # Load status mapping from presets
        event_settings = (
            project_settings["ftrack"]["events"]["next_task_update"]
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

        self.set_next_task_statuses(
            session,
            tasks_by_parent_id,
            event_task_ids_by_parent_id,
            statuses
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
        statuses
    ):
        statuses_by_low_name = {
            status["name"].lower(): status
            for status in statuses
        }
        next_status_name = "Ready"
        next_status = statuses_by_low_name.get(next_status_name.lower())
        if not next_status:
            self.log.warning("Couldn't find status with name \"{}\"".format(
                next_status_name
            ))
            return

        statuses_by_id = {
            status["id"].lower(): status
            for status in statuses
        }

        sorted_task_type_ids = self.get_sorted_task_type_ids(session)

        for parent_id, _task_entities in tasks_by_parent_id.items():
            task_entities_by_type_id = collections.defaultdict(list)
            for _task_entity in _task_entities:
                type_id = _task_entity["type_id"]
                task_entities_by_type_id[type_id].append(_task_entity)

            event_ids = set(event_task_ids_by_parent_id[parent_id])
            next_tasks = []
            for type_id in sorted_task_type_ids:
                if type_id not in task_entities_by_type_id:
                    continue

                all_in_type_done = True
                task_entities = task_entities_by_type_id[type_id]
                if not event_ids:
                    next_tasks = task_entities
                    break

                for task_entity in task_entities:
                    task_id = task_entity["id"]
                    if task_id in event_ids:
                        event_ids.remove(task_id)

                    task_status = statuses_by_id[task_entity["status_id"]]
                    low_status_name = task_status["name"].lower()
                    if low_status_name == "omitted":
                        continue

                    low_state_name = task_status["state"]["name"].lower()
                    if low_state_name != "done":
                        all_in_type_done = False
                        break

                if not all_in_type_done:
                    break

            if not next_tasks:
                continue

            for task_entity in next_tasks:
                task_status = statuses_by_id[task_entity["status_id"]]
                if task_status["name"].lower() != "not ready":
                    continue

                ent_path = "/".join(
                    [ent["name"] for ent in task_entity["link"]]
                )
                try:
                    task_entity["status_id"] = next_status["id"]
                    session.commit()
                    self.log.info(
                        "\"{}\" updated status to \"{}\"".format(
                            ent_path, next_status_name
                        )
                    )
                except Exception:
                    session.rollback()
                    self.log.warning(
                        "\"{}\" status couldnt be set to \"{}\"".format(
                            ent_path, next_status_name
                        ),
                        exc_info=True
                    )

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


def register(session, plugins_presets):
    NextTaskUpdate(session, plugins_presets).register()
