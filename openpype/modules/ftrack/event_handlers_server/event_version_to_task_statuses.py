from openpype_modules.ftrack.lib import BaseEvent


class VersionToTaskStatus(BaseEvent):
    """Propagates status from version to task when changed."""
    def launch(self, session, event):
        # Filter event entities
        # - output is dictionary where key is project id and event info in
        #   value
        filtered_entities_info = self.filter_entity_info(event)
        if not filtered_entities_info:
            return

        for project_id, entities_info in filtered_entities_info.items():
            self.process_by_project(session, event, project_id, entities_info)

    def filter_entity_info(self, event):
        filtered_entity_info = {}
        for entity_info in event["data"].get("entities", []):
            # Filter AssetVersions
            if entity_info["entityType"] != "assetversion":
                continue

            # Skip if statusid not in keys (in changes)
            keys = entity_info.get("keys")
            if not keys or "statusid" not in keys:
                continue

            # Get new version task name
            version_status_id = (
                entity_info
                .get("changes", {})
                .get("statusid", {})
                .get("new", {})
            )

            # Just check that `new` is set to any value
            if not version_status_id:
                continue

            # Get project id from entity info
            project_id = entity_info["parents"][-1]["entityId"]
            if project_id not in filtered_entity_info:
                filtered_entity_info[project_id] = []
            filtered_entity_info[project_id].append(entity_info)
        return filtered_entity_info

    def process_by_project(self, session, event, project_id, entities_info):
        # Check for project data if event is enabled for event handler
        project_name = self.get_project_name_from_event(
            session, event, project_id
        )
        # Load settings
        project_settings = self.get_project_settings_from_event(
            event, project_name
        )

        # Load status mapping from presets
        event_settings = (
            project_settings["ftrack"]["events"]["status_version_to_task"]
        )
        # Skip if event is not enabled or status mapping is not set
        if not event_settings["enabled"]:
            self.log.debug("Project \"{}\" has disabled {}".format(
                project_name, self.__class__.__name__
            ))
            return

        _status_mapping = event_settings["mapping"] or {}
        status_mapping = {
            key.lower(): value
            for key, value in _status_mapping.items()
        }

        asset_types_to_skip = [
            short_name.lower()
            for short_name in event_settings["asset_types_to_skip"]
        ]

        # Collect entity ids
        asset_version_ids = set()
        for entity_info in entities_info:
            asset_version_ids.add(entity_info["entityId"])

        # Query tasks for AssetVersions
        _asset_version_entities = session.query(
            "AssetVersion where task_id != none and id in ({})".format(
                self.join_query_keys(asset_version_ids)
            )
        ).all()
        if not _asset_version_entities:
            return

        # Filter asset versions by asset type and store their task_ids
        task_ids = set()
        asset_version_entities = []
        for asset_version in _asset_version_entities:
            if asset_types_to_skip:
                short_name = asset_version["asset"]["type"]["short"].lower()
                if short_name in asset_types_to_skip:
                    continue
            asset_version_entities.append(asset_version)
            task_ids.add(asset_version["task_id"])

        # Skipt if `task_ids` are empty
        if not task_ids:
            return

        task_entities = session.query(
            "select link from Task where id in ({})".format(
                self.join_query_keys(task_ids)
            )
        ).all()
        task_entities_by_id = {
            task_entiy["id"]: task_entiy
            for task_entiy in task_entities
        }

        # Prepare asset version by their id
        asset_versions_by_id = {
            asset_version["id"]: asset_version
            for asset_version in asset_version_entities
        }

        # Query status entities
        status_ids = set()
        for entity_info in entities_info:
            # Skip statuses of asset versions without task
            if entity_info["entityId"] not in asset_versions_by_id:
                continue
            status_ids.add(entity_info["changes"]["statusid"]["new"])

        version_status_entities = session.query(
            "select id, name from Status where id in ({})".format(
                self.join_query_keys(status_ids)
            )
        ).all()

        # Qeury statuses
        statusese_by_obj_id = self.statuses_for_tasks(
            session, task_entities, project_id
        )
        # Prepare status names by their ids
        status_name_by_id = {
            status_entity["id"]: status_entity["name"]
            for status_entity in version_status_entities
        }
        for entity_info in entities_info:
            entity_id = entity_info["entityId"]
            status_id = entity_info["changes"]["statusid"]["new"]
            status_name = status_name_by_id.get(status_id)
            if not status_name:
                continue
            status_name_low = status_name.lower()

            # Lower version status name and check if has mapping
            new_status_names = []
            mapped = status_mapping.get(status_name_low)
            if mapped:
                new_status_names.extend(list(mapped))

            new_status_names.append(status_name_low)

            self.log.debug(
                "Processing AssetVersion status change: [ {} ]".format(
                    status_name
                )
            )

            asset_version = asset_versions_by_id[entity_id]
            task_entity = task_entities_by_id[asset_version["task_id"]]
            type_id = task_entity["type_id"]

            # Lower all names from presets
            new_status_names = [name.lower() for name in new_status_names]
            task_statuses_by_low_name = statusese_by_obj_id[type_id]

            new_status = None
            for status_name in new_status_names:
                if status_name not in task_statuses_by_low_name:
                    self.log.debug((
                        "Task does not have status name \"{}\" available."
                    ).format(status_name))
                    continue

                # store object of found status
                new_status = task_statuses_by_low_name[status_name]
                self.log.debug("Status to set: [ {} ]".format(
                    new_status["name"]
                ))
                break

            # Skip if status names were not found for paticulat entity
            if not new_status:
                self.log.warning(
                    "Any of statuses from presets can be set: {}".format(
                        str(new_status_names)
                    )
                )
                continue
            # Get full path to task for logging
            ent_path = "/".join([ent["name"] for ent in task_entity["link"]])

            # Setting task status
            try:
                task_entity["status"] = new_status
                session.commit()
                self.log.debug("[ {} ] Status updated to [ {} ]".format(
                    ent_path, new_status["name"]
                ))
            except Exception:
                session.rollback()
                self.log.warning(
                    "[ {} ]Status couldn't be set".format(ent_path),
                    exc_info=True
                )

    def statuses_for_tasks(self, session, task_entities, project_id):
        task_type_ids = set()
        for task_entity in task_entities:
            task_type_ids.add(task_entity["type_id"])

        project_entity = session.get("Project", project_id)
        project_schema = project_entity["project_schema"]
        output = {}
        for task_type_id in task_type_ids:
            statuses = project_schema.get_statuses("Task", task_type_id)
            output[task_type_id] = {
                status["name"].lower(): status
                for status in statuses
            }

        return output


def register(session):
    '''Register plugin. Called when used as an plugin.'''

    VersionToTaskStatus(session).register()
