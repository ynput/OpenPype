import operator
import collections
from pype.modules.ftrack import BaseEvent


class NextTaskUpdate(BaseEvent):
    def filter_entities_info(self, session, event):
        # Filter if event contain relevant data
        entities_info = event["data"].get("entities")
        if not entities_info:
            return

        first_filtered_entities = []
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

            first_filtered_entities.append(entity_info)

        status_ids = [
            entity_info["changes"]["statusid"]["new"]
            for entity_info in first_filtered_entities
        ]
        statuses_by_id = self.get_statuses_by_id(
            session, status_ids=status_ids
        )

        # Care only about tasks having status with state `Done`
        filtered_entities = []
        for entity_info in first_filtered_entities:
            status_id = entity_info["changes"]["statusid"]["new"]
            status_entity = statuses_by_id[status_id]
            if status_entity["state"]["name"].lower() == "done":
                filtered_entities.append(entity_info)

        return filtered_entities

    def get_parents_by_id(self, session, entities_info):
        parent_ids = [
            "\"{}\"".format(entity_info["parentId"])
            for entity_info in entities_info
        ]
        parent_entities = session.query(
            "TypedContext where id in ({})".format(", ".join(parent_ids))
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

    def get_sorted_task_types(self, session):
        data = {
            _type: _type.get("sort")
            for _type in session.query("Type").all()
            if _type.get("sort") is not None
        }

        return [
            item[0]
            for item in sorted(data.items(), key=operator.itemgetter(1))
        ]

    def launch(self, session, event):
        '''Propagates status from version to task when changed'''

        entities_info = self.filter_entities_info(session, event)
        if not entities_info:
            return

        parents_by_id = self.get_parents_by_id(session, entities_info)
        tasks_by_id = self.get_tasks_by_id(
            session, tuple(parents_by_id.keys())
        )

        tasks_to_parent_id = collections.defaultdict(list)
        for task_entity in tasks_by_id.values():
            tasks_to_parent_id[task_entity["parent_id"]].append(task_entity)

        statuses_by_id = self.get_statuses_by_id(session, tasks_by_id.values())

        next_status_name = "Ready"
        next_status = session.query(
            "Status where name is \"{}\"".format(next_status_name)
        ).first()
        if not next_status:
            self.log.warning("Couldn't find status with name \"{}\"".format(
                next_status_name
            ))
            return

        for entity_info in entities_info:
            parent_id = entity_info["parentId"]
            task_id = entity_info["entityId"]
            task_entity = tasks_by_id[task_id]

            all_same_type_taks_done = True
            for parents_task in tasks_to_parent_id[parent_id]:
                if (
                    parents_task["id"] == task_id
                    or parents_task["type_id"] != task_entity["type_id"]
                ):
                    continue

                parents_task_status = statuses_by_id[parents_task["status_id"]]
                low_status_name = parents_task_status["name"].lower()
                # Skip if task's status name "Omitted"
                if low_status_name == "omitted":
                    continue

                low_state_name = parents_task_status["state"]["name"].lower()
                if low_state_name != "done":
                    all_same_type_taks_done = False
                    break

            if not all_same_type_taks_done:
                continue

            # Prepare all task types
            sorted_task_types = self.get_sorted_task_types(session)
            sorted_task_types_len = len(sorted_task_types)

            from_idx = None
            for idx, task_type in enumerate(sorted_task_types):
                if task_type["id"] == task_entity["type_id"]:
                    from_idx = idx + 1
                    break

            # Current task type is last in order
            if from_idx is None or from_idx >= sorted_task_types_len:
                continue

            next_task_type_id = None
            next_task_type_tasks = []
            for idx in range(from_idx, sorted_task_types_len):
                next_task_type = sorted_task_types[idx]
                for parents_task in tasks_to_parent_id[parent_id]:
                    if next_task_type_id is None:
                        if parents_task["type_id"] != next_task_type["id"]:
                            continue
                        next_task_type_id = next_task_type["id"]

                    if parents_task["type_id"] == next_task_type_id:
                        next_task_type_tasks.append(parents_task)

                if next_task_type_id is not None:
                    break

            for next_task_entity in next_task_type_tasks:
                if next_task_entity["status"]["name"].lower() != "not ready":
                    continue

                ent_path = "/".join(
                    [ent["name"] for ent in next_task_entity["link"]]
                )
                try:
                    next_task_entity["status"] = next_status
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


def register(session, plugins_presets):
    NextTaskUpdate(session, plugins_presets).register()
