from pype.modules.ftrack import BaseEvent
from pype.api import get_project_settings


class VersionToTaskStatus(BaseEvent):
    # TODO remove `join_query_keys` as it should be in `BaseHandler`
    @staticmethod
    def join_query_keys(keys):
        """Helper to join keys to query."""
        return ",".join(["\"{}\"".format(key) for key in keys])

    def filter_entity_info(self, event):
        filtered_entity_info = []
        for entity in event["data"].get("entities", []):
            # Filter AssetVersions
            if entity["entityType"] != "assetversion":
                continue

            # Skip if statusid not in keys (in changes)
            keys = entity.get("keys")
            if not keys or "statusid" not in keys:
                continue

            # Get new version task name
            version_status_id = (
                entity
                .get("changes", {})
                .get("statusid", {})
                .get("new", {})
            )

            # Just check that `new` is set to any value
            if version_status_id:
                filtered_entity_info.append(filtered_entity_info)
        return filtered_entity_info

    def prepare_project_data(self, session, event, task_entities):
        output = {
            "status_mapping": None,
            "task_statuses": None
        }

        # Try to get project entity from event
        project_entity = event["data"].get("project_entity")
        if not project_entity:
            # Get project entity from task and store to event
            project_entity = self.get_project_from_entity(task_entities[0])
            event["data"]["project_entity"] = project_entity

        project_name = project_entity["full_name"]
        project_settings = get_project_settings(project_name)

        # Load status mapping from presets
        event_settings = (
            project_settings["ftrack"]["events"]["status_version_to_task"]
        )
        # Skip if event is not enabled or status mapping is not set
        if not event_settings["enabled"]:
            self.log.debug("Project \"{}\" has disabled {}".format(
                project_name, self.__class__.__name__
            ))
            return output

        status_mapping = event_settings["mapping"]
        if not status_mapping:
            self.log.debug(
                "Project \"{}\" does not have set mapping for {}".format(
                    project_name, self.__class__.__name__
                )
            )
            return output

        # Store status mapping to output
        output["status_mapping"] = status_mapping

        task_object_type = session.query(
            "ObjectType where name is \"Task\""
        ).one()

        project_schema = project_entity["project_schema"]
        # Get all available statuses for Task and store to output
        output["task_statuses"] = list(project_schema.get_statuses(
            "Task", task_object_type["id"]
        ))

        return output

    def launch(self, session, event):
        '''Propagates status from version to task when changed'''

        filtered_entities_info = self.filter_entity_info(event)
        if not filtered_entities_info:
            return

        # Collect entity ids
        asset_version_ids = set()
        for entity_info in filtered_entities_info:
            asset_version_ids.add(entity_info["entityId"])

        # Query tasks for AssetVersions
        _asset_version_entities = session.query(
            "AsserVersion where task_id != none and id in ({})".format(
                self.join_query_keys(asset_version_ids)
            )
        ).all()
        if not _asset_version_entities:
            return

        # Filter asset versions by asset type and store their task_ids
        task_ids = set()
        asset_version_entities = []
        for asset_version in _asset_version_entities:
            if asset_version["asset"]["type"]["short"].lower() == "scene":
                continue
            asset_version_entities.append(asset_version)
            task_ids.add(asset_version["task_id"])

        # Skipt if `task_ids` are empty
        if not task_ids:
            return
        asset_versions_by_id = {
            asset_version["id"]: asset_version
            for asset_version in asset_version_entities
        }

        # Query status entities
        status_ids = set()
        for entity_info in filtered_entities_info:
            # Skip statuses of asset versions without task
            if entity_info["entityId"] not in asset_versions_by_id:
                continue
            status_ids.add(entity_info["changes"]["statusid"]["new"])

            try:
                version_status = session.get("Status", version_status_id)
            except Exception:
                self.log.warning(
                    "Troubles with query status id [ {} ]".format(
                        version_status_id
                    ),
                    exc_info=True
                )

            if not version_status:
                continue

            version_status_orig = version_status["name"]

            # Get entities necessary for processing
            version = session.get("AssetVersion", entity["entityId"])
            task = version.get("task")
            if not task:
                continue

            project_entity = self.get_project_from_entity(task)
            project_name = project_entity["full_name"]
            project_settings = get_project_settings(project_name)

            # Load status mapping from presets
            status_mapping = (
                project_settings["ftrack"]["events"]["status_version_to_task"])
            # Skip if mapping is empty
            if not status_mapping:
                continue

            # Lower version status name and check if has mapping
            version_status = version_status_orig.lower()
            new_status_names = []
            mapped = status_mapping.get(version_status)
            if mapped:
                new_status_names.extend(list(mapped))

            new_status_names.append(version_status)

            self.log.debug(
                "Processing AssetVersion status change: [ {} ]".format(
                    version_status_orig
                )
            )

            # Lower all names from presets
            new_status_names = [name.lower() for name in new_status_names]

            if version["asset"]["type"]["short"].lower() == "scene":
                continue

            project_schema = project_entity["project_schema"]
            # Get all available statuses for Task
            statuses = project_schema.get_statuses("Task", task["type_id"])
            # map lowered status name with it's object
            stat_names_low = {
                status["name"].lower(): status for status in statuses
            }

            new_status = None
            for status_name in new_status_names:
                if status_name not in stat_names_low:
                    continue

                # store object of found status
                new_status = stat_names_low[status_name]
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
            ent_path = "/".join([ent["name"] for ent in task["link"]])

            # Setting task status
            try:
                task["status"] = new_status
                session.commit()
                self.log.debug("[ {} ] Status updated to [ {} ]".format(
                    ent_path, new_status['name']
                ))
            except Exception:
                session.rollback()
                self.log.warning(
                    "[ {} ]Status couldn't be set".format(ent_path),
                    exc_info=True
                )


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''

    VersionToTaskStatus(session, plugins_presets).register()
