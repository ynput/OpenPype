from openpype_modules.ftrack.lib import BaseEvent


class FirstVersionStatus(BaseEvent):

    # WARNING Priority MUST be higher
    # than handler in `event_version_to_task_statuses.py`
    priority = 200

    keys_enum = ["task", "task_type"]
    # This should be set with presets
    task_status_map = []

    # EXAMPLE of `task_status_map`
    __example_status_map__ = [{
        # `key` specify where to look for name (is enumerator of `keys_enum`)
        # By default is set to "task"
        "key": "task",
        # speicification of name
        "name": "compositing",
        # Status to set to the asset version
        "status": "Blocking"
    }]

    def register(self, *args, **kwargs):
        result = super(FirstVersionStatus, self).register(*args, **kwargs)

        valid_task_status_map = []
        for item in self.task_status_map:
            key = (item.get("key") or "task").lower()
            name = (item.get("name") or "").lower()
            status = (item.get("status") or "").lower()
            if not (key and name and status):
                self.log.warning((
                    "Invalid item in Task -> Status mapping. {}"
                ).format(str(item)))
                continue

            if key not in self.keys_enum:
                expected_msg = ""
                last_key_idx = len(self.keys_enum) - 1
                for idx, key in enumerate(self.keys_enum):
                    if idx == 0:
                        joining_part = "`{}`"
                    elif idx == last_key_idx:
                        joining_part = "or `{}`"
                    else:
                        joining_part = ", `{}`"
                    expected_msg += joining_part.format(key)

                self.log.warning((
                    "Invalid key `{}`. Expected: {}."
                ).format(key, expected_msg))
                continue

            valid_task_status_map.append({
                "key": key,
                "name": name,
                "status": status
            })

        self.task_status_map = valid_task_status_map
        if not self.task_status_map:
            self.log.warning((
                "Event handler `{}` don't have set presets."
            ).format(self.__class__.__name__))

        return result

    def launch(self, session, event):
        """Set task's status for first created Asset Version."""

        if not self.task_status_map:
            return

        entities_info = self.filter_event_ents(event)
        if not entities_info:
            return

        entity_ids = []
        for entity_info in entities_info:
            entity_ids.append(entity_info["entityId"])

        joined_entity_ids = ",".join(
            ["\"{}\"".format(entity_id) for entity_id in entity_ids]
        )
        asset_versions = session.query(
            "AssetVersion where id in ({})".format(joined_entity_ids)
        ).all()

        asset_version_statuses = None

        project_schema = None
        for asset_version in asset_versions:
            task_entity = asset_version["task"]
            found_item = None
            for item in self.task_status_map:
                if (
                    item["key"] == "task" and
                    task_entity["name"].lower() != item["name"]
                ):
                    continue

                elif (
                    item["key"] == "task_type" and
                    task_entity["type"]["name"].lower() != item["name"]
                ):
                    continue

                found_item = item
                break

            if not found_item:
                continue

            if project_schema is None:
                project_schema = task_entity["project"]["project_schema"]

            # Get all available statuses for Task
            if asset_version_statuses is None:
                statuses = project_schema.get_statuses("AssetVersion")

                # map lowered status name with it's object
                asset_version_statuses = {
                    status["name"].lower(): status for status in statuses
                }

            ent_path = "/".join(
                [ent["name"] for ent in task_entity["link"]] +
                [
                    str(asset_version["asset"]["name"]),
                    str(asset_version["version"])
                ]
            )

            new_status = asset_version_statuses.get(found_item["status"])
            if not new_status:
                self.log.warning(
                    "AssetVersion doesn't have status `{}`."
                ).format(found_item["status"])
                continue

            try:
                asset_version["status"] = new_status
                session.commit()
                self.log.debug("[ {} ] Status updated to [ {} ]".format(
                    ent_path, new_status['name']
                ))

            except Exception:
                session.rollback()
                self.log.warning(
                    "[ {} ] Status couldn't be set.".format(ent_path),
                    exc_info=True
                )

    def filter_event_ents(self, event):
        filtered_ents = []
        for entity in event["data"].get("entities", []):
            # Care only about add actions
            if entity.get("action") != "add":
                continue

            # Filter AssetVersions
            if entity["entityType"] != "assetversion":
                continue

            entity_changes = entity.get("changes") or {}

            # Check if version of Asset Version is `1`
            version_num = entity_changes.get("version", {}).get("new")
            if version_num != 1:
                continue

            # Skip in Asset Version don't have task
            task_id = entity_changes.get("taskid", {}).get("new")
            if not task_id:
                continue

            filtered_ents.append(entity)

        return filtered_ents


def register(session):
    '''Register plugin. Called when used as an plugin.'''

    FirstVersionStatus(session).register()
