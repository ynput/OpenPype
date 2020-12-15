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

        task_entities = session.query(
            "select project_id from Task where id in ({})".format(
                self.join_query_keys(task_ids)
            )
        ).all()
        task_entities_by_id = {
            task_entiy["id"]: task_entiy
            for task_entiy in task_entities
        }
        project_data = self.prepare_project_data(
            session, event, task_entities
        )

        if (
            not project_data["status_mapping"]
            or not project_data["task_statuses"]
        ):
            return

        # Prepare asset version by their id
        asset_versions_by_id = {
            asset_version["id"]: asset_version
            for asset_version in asset_version_entities
        }

        status_mapping = project_data["status_mapping"]
        task_statuses = project_data["task_statuses"]

        # map lowered status name with it's object
        task_statuses_by_low_name = {
            status["name"].lower(): status
            for status in task_statuses
        }

        # Query status entities
        status_ids = set()
        for entity_info in filtered_entities_info:
            # Skip statuses of asset versions without task
            if entity_info["entityId"] not in asset_versions_by_id:
                continue
            status_ids.add(entity_info["changes"]["statusid"]["new"])

        # Qeury statuses
        status_entities = session.query(
            "select id, name from Status where id in ({})".format(
                self.join_query_keys(status_ids)
            )
        ).all()
        # Prepare status names by their ids
        status_name_by_id = {
            status_entity["id"]: status_entity["name"]
            for status_entity in status_entities
        }
        for entity_info in filtered_entities_info:
            entity_id = entity_info["entityId"]
            status_id = entity_info["changes"]["statusid"]["new"]
            status_name = status_name_by_id.get(status_id)
            status_name_low = status_name.lower()
            if not status_name_low:
                continue

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

            # Lower all names from presets
            new_status_names = [name.lower() for name in new_status_names]

            new_status = None
            for status_name in new_status_names:
                if status_name not in task_statuses_by_low_name:
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

            asset_version = asset_versions_by_id[entity_id]
            task_entity = task_entities_by_id[asset_version["task_id"]]
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


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''

    VersionToTaskStatus(session, plugins_presets).register()
